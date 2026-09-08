import Layout from "../../components/Layout";
import { useAuth } from "../../context/AuthContext";

export default function AdminHome() {
  const { user, role } = useAuth();
  return (
    <Layout>
      <h1 className="h3">Bienvenido, {user?.username} ({role})</h1>
    </Layout>
  );
}
