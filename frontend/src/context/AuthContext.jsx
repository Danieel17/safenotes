import { createContext, useContext, useEffect, useState } from "react";
import apiClient from "../api/client";

const AuthContext = createContext(null);

function decodeJwtPayload(token) {
  try {
    const payloadSegment = token.split(".")[1];
    // base64url -> base64
    const base64 = payloadSegment.replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    const json = atob(padded);
    return JSON.parse(json);
  } catch (err) {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [role, setRole] = useState(null);
  const [loading, setLoading] = useState(true);

  async function hydrateFromStoredTokens() {
    const access = localStorage.getItem("access");
    if (!access) {
      setLoading(false);
      return;
    }
    const payload = decodeJwtPayload(access);
    if (!payload) {
      setLoading(false);
      return;
    }
    setRole(payload.role || null);
    // The JWT only carries user_id/role, not username; fetch the profile to
    // populate the display name. Best-effort: if it fails (e.g. expired
    // access token with no valid refresh), the axios interceptor will
    // handle clearing the session.
    try {
      const { data } = await apiClient.get("profile/");
      setUser({ username: data.username, email: data.email, role: data.role });
      setRole(data.role);
    } catch (err) {
      setUser({ username: payload.username || null });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    hydrateFromStoredTokens();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function login(username, password) {
    const { data } = await apiClient.post("auth/token/", { username, password });
    localStorage.setItem("access", data.access);
    localStorage.setItem("refresh", data.refresh);

    const payload = decodeJwtPayload(data.access);
    const nextRole = payload?.role || null;
    setRole(nextRole);

    try {
      const profileResp = await apiClient.get("profile/");
      setUser({
        username: profileResp.data.username,
        email: profileResp.data.email,
        role: profileResp.data.role,
      });
      setRole(profileResp.data.role);
    } catch (err) {
      setUser({ username });
    }

    return { role: nextRole };
  }

  async function logout() {
    const refresh = localStorage.getItem("refresh");
    try {
      if (refresh) {
        await apiClient.post("auth/logout/", { refresh });
      }
    } catch (err) {
      // Best-effort: don't let a network failure trap the user in a
      // logged-in-looking state.
    } finally {
      localStorage.removeItem("access");
      localStorage.removeItem("refresh");
      setUser(null);
      setRole(null);
    }
  }

  const value = {
    user,
    role,
    login,
    logout,
    isAuthenticated: Boolean(user || localStorage.getItem("access")),
    loading,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
