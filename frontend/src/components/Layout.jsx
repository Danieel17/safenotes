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
