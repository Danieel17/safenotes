import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import ProtectedRoute from "./routes/ProtectedRoute";
import RoleRoute from "./routes/RoleRoute";
import LoginPage from "./pages/LoginPage";
import AdminHome from "./pages/admin/AdminHome";
import EditorHome from "./pages/editor/EditorHome";
import LectorHome from "./pages/lector/LectorHome";

const ROLE_LANDING = {
  admin: "/admin",
  editor: "/notes",
  lector: "/shared",
};

function RoleBasedLanding() {
  const { role, loading } = useAuth();
  if (loading) return null;
  return <Navigate to={ROLE_LANDING[role] || "/login"} replace />;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <RoleBasedLanding />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <ProtectedRoute>
            <RoleRoute role="admin">
              <AdminHome />
            </RoleRoute>
          </ProtectedRoute>
        }
      />
      <Route
        path="/notes"
        element={
          <ProtectedRoute>
            <RoleRoute role="editor">
              <EditorHome />
            </RoleRoute>
          </ProtectedRoute>
        }
      />
      <Route
        path="/shared"
        element={
          <ProtectedRoute>
            <RoleRoute role="lector">
              <LectorHome />
            </RoleRoute>
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
