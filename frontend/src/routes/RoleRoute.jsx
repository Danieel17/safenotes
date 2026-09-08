import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

// UX convenience only, NOT a security boundary. This component just hides
// nav/routes the current role shouldn't see in the normal flow; the real
// authorization enforcement lives server-side via DRF permission classes
// (see ticket 01/02). A malicious or modified client could bypass this
// entirely, so every API endpoint must independently check role/ownership.
export default function RoleRoute({ role, children }) {
  const { role: currentRole, loading } = useAuth();
  const allowedRoles = Array.isArray(role) ? role : [role];

  if (loading) {
    return null;
  }

  if (!currentRole || !allowedRoles.includes(currentRole)) {
    return <Navigate to="/" replace />;
  }

  return children;
}
