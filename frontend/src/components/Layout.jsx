import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const ROLE_HOME = {
  admin: "/admin",
  editor: "/notes",
  lector: "/shared",
};

const ROLE_LABEL = {
  admin: "Administrador",
  editor: "Editor",
  lector: "Lector",
};

export default function Layout({ children }) {
  const { user, role, logout } = useAuth();
  const homeLink = ROLE_HOME[role] || "/";

  return (
    <div className="sn-layout d-flex">
      <aside className="sn-sidebar">
        <span className="sn-brand">
          <i className="bi bi-shield-lock-fill" /> SafeNotes
        </span>

        <div className="sn-user-box">
          <span className="sn-username">{user?.username || "..."}</span>
          {role && <span className={`badge sn-badge-${role}`}>{ROLE_LABEL[role] || role}</span>}
        </div>

        <nav className="nav flex-column">
          <Link className="nav-link" to={homeLink}>
            <i className="bi bi-house-door" /> Inicio
          </Link>

          {role === "admin" && (
            <>
              <span className="sn-section-title">Administración</span>
              <Link className="nav-link" to="/admin/users">
                <i className="bi bi-people" /> Usuarios
              </Link>
              <Link className="nav-link" to="/admin/categories">
                <i className="bi bi-tags" /> Categorías
              </Link>
              <Link className="nav-link" to="/admin/audit-log">
                <i className="bi bi-journal-text" /> Auditoría
              </Link>
            </>
          )}

          {role === "editor" && (
            <>
              <span className="sn-section-title">Editor</span>
              <Link className="nav-link" to="/notes">
                <i className="bi bi-journal-text" /> Mis notas
              </Link>
            </>
          )}

          {role === "lector" && (
            <>
              <span className="sn-section-title">Lector</span>
              <Link className="nav-link" to="/shared">
                <i className="bi bi-journal-text" /> Notas compartidas
              </Link>
              <Link className="nav-link" to="/folders">
                <i className="bi bi-folder2" /> Carpetas
              </Link>
            </>
          )}

          <span className="sn-section-title">Cuenta</span>
          <Link className="nav-link" to="/profile">
            <i className="bi bi-person-circle" /> Mi Perfil
          </Link>
        </nav>

        <div className="sn-logout">
          <button className="btn btn-outline-light btn-sm w-100" type="button" onClick={logout}>
            <i className="bi bi-box-arrow-right" /> Cerrar sesión
          </button>
        </div>
      </aside>

      <div className="sn-content">
        <main className="sn-main">{children}</main>
      </div>
    </div>
  );
}
