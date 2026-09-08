import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

// Client-side convenience only: redirects unauthenticated users away from
// protected pages so the UI doesn't flash empty/broken screens. This is NOT
// a security boundary — the DRF API enforces authentication server-side
// regardless of what this component does.
export default function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return null;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
