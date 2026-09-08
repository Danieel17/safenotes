import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import ProtectedRoute from "./routes/ProtectedRoute";
import RoleRoute from "./routes/RoleRoute";
import LoginPage from "./pages/LoginPage";
import AdminHome from "./pages/admin/AdminHome";
import UsersPage from "./pages/admin/UsersPage";
import CategoriesPage from "./pages/admin/CategoriesPage";
import AuditLogPage from "./pages/admin/AuditLogPage";
import ProfilePage from "./pages/shared/ProfilePage";
import NotesListPage from "./pages/editor/NotesListPage";
import NoteFormPage from "./pages/editor/NoteFormPage";
import NoteDetailPage from "./pages/editor/NoteDetailPage";
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
        path="/admin/users"
        element={
          <ProtectedRoute>
            <RoleRoute role="admin">
              <UsersPage />
            </RoleRoute>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/categories"
        element={
          <ProtectedRoute>
            <RoleRoute role="admin">
              <CategoriesPage />
            </RoleRoute>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/audit-log"
        element={
          <ProtectedRoute>
            <RoleRoute role="admin">
              <AuditLogPage />
            </RoleRoute>
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <ProfilePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/notes"
        element={
          <ProtectedRoute>
            <RoleRoute role="editor">
              <NotesListPage />
            </RoleRoute>
          </ProtectedRoute>
        }
      />
      <Route
        path="/notes/new"
        element={
          <ProtectedRoute>
            <RoleRoute role="editor">
              <NoteFormPage />
            </RoleRoute>
          </ProtectedRoute>
        }
      />
      <Route
        path="/notes/:id"
        element={
          <ProtectedRoute>
            <RoleRoute role="editor">
              <NoteDetailPage />
            </RoleRoute>
          </ProtectedRoute>
        }
      />
      <Route
        path="/notes/:id/edit"
        element={
          <ProtectedRoute>
            <RoleRoute role="editor">
              <NoteFormPage />
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
