import { Link } from "react-router-dom";
import Layout from "../../components/Layout";
import { useAuth } from "../../context/AuthContext";

export default function AdminHome() {
  const { user } = useAuth();
  return (
    <Layout>
      <h1 className="h3 mb-4">Bienvenido, {user?.username}</h1>
      <div className="row g-3">
        <div className="col-md-4">
          <Link to="/admin/users" className="sn-card p-3 d-block text-decoration-none">
            <h2 className="h5 card-title">Usuarios</h2>
            <p className="mb-0 text-muted">Crear cuentas, activar/desactivar y cambiar roles.</p>
          </Link>
        </div>
        <div className="col-md-4">
          <Link to="/admin/categories" className="sn-card p-3 d-block text-decoration-none">
            <h2 className="h5 card-title">Categorías</h2>
            <p className="mb-0 text-muted">Gestionar categorías disponibles para las notas.</p>
          </Link>
        </div>
        <div className="col-md-4">
          <Link to="/admin/audit-log" className="sn-card p-3 d-block text-decoration-none">
            <h2 className="h5 card-title">Auditoría</h2>
            <p className="mb-0 text-muted">Revisar el registro de acciones del sistema.</p>
          </Link>
        </div>
      </div>
    </Layout>
  );
}
