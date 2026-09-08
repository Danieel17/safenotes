import { useEffect, useState } from "react";
import Layout from "../../components/Layout";
import apiClient from "../../api/client";

const ROLE_LABEL = {
  admin: "Administrador",
  editor: "Editor",
  lector: "Lector",
};

function extractError(err, fallback) {
  const data = err?.response?.data;
  if (!data) return fallback;
  if (typeof data === "string") return data;
  if (data.detail) return data.detail;
  const parts = Object.entries(data).map(([field, msgs]) => {
    const msg = Array.isArray(msgs) ? msgs.join(" ") : String(msgs);
    return field === "non_field_errors" ? msg : `${field}: ${msg}`;
  });
  return parts.length ? parts.join(" | ") : fallback;
}

export default function UsersPage() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState("");

  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ username: "", password: "", role: "editor" });
  const [createError, setCreateError] = useState("");
  const [creating, setCreating] = useState(false);

  const [roleDrafts, setRoleDrafts] = useState({});
  const [rowError, setRowError] = useState({});
  const [rowBusy, setRowBusy] = useState({});

  async function fetchUsers() {
    setLoading(true);
    setListError("");
    try {
      const { data } = await apiClient.get("users/");
      const results = Array.isArray(data) ? data : data.results || [];
      setUsers(results);
    } catch (err) {
      setListError(extractError(err, "No se pudo cargar la lista de usuarios."));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchUsers();
  }, []);

  async function handleCreate(e) {
    e.preventDefault();
    setCreateError("");
    setCreating(true);
    try {
      await apiClient.post("users/", form);
      setForm({ username: "", password: "", role: "editor" });
      setShowCreate(false);
      await fetchUsers();
    } catch (err) {
      setCreateError(extractError(err, "No se pudo crear el usuario."));
    } finally {
      setCreating(false);
    }
  }

  async function handleToggleActive(user) {
    setRowError((prev) => ({ ...prev, [user.id]: "" }));
    setRowBusy((prev) => ({ ...prev, [user.id]: true }));
    try {
      await apiClient.post(`users/${user.id}/toggle-active/`);
      await fetchUsers();
    } catch (err) {
      setRowError((prev) => ({ ...prev, [user.id]: extractError(err, "Acción rechazada.") }));
    } finally {
      setRowBusy((prev) => ({ ...prev, [user.id]: false }));
    }
  }

  async function handleRoleChange(user) {
    const nextRole = roleDrafts[user.id] || user.role;
    if (nextRole === user.role) return;
    setRowError((prev) => ({ ...prev, [user.id]: "" }));
    setRowBusy((prev) => ({ ...prev, [user.id]: true }));
    try {
      await apiClient.post(`users/${user.id}/role/`, { role: nextRole });
      await fetchUsers();
    } catch (err) {
      setRowError((prev) => ({ ...prev, [user.id]: extractError(err, "Acción rechazada.") }));
    } finally {
      setRowBusy((prev) => ({ ...prev, [user.id]: false }));
    }
  }

  return (
    <Layout>
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h1 className="h3 mb-0">Usuarios</h1>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => {
            setShowCreate((v) => !v);
            setCreateError("");
          }}
        >
          <i className="bi bi-person-plus" /> Crear usuario
        </button>
      </div>

      {showCreate && (
        <div className="sn-card p-3 mb-4">
          <h2 className="h6">Nuevo usuario</h2>
          {createError && <div className="alert alert-danger py-2">{createError}</div>}
          <form onSubmit={handleCreate} className="row g-2 align-items-end">
            <div className="col-md-4">
              <label className="form-label">Usuario</label>
              <input
                className="form-control"
                required
                value={form.username}
                onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
              />
            </div>
            <div className="col-md-4">
              <label className="form-label">Contraseña</label>
              <input
                type="password"
                className="form-control"
                required
                value={form.password}
                onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
              />
            </div>
            <div className="col-md-2">
              <label className="form-label">Rol</label>
              <select
                className="form-select"
                value={form.role}
                onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
              >
                <option value="editor">Editor</option>
                <option value="lector">Lector</option>
              </select>
            </div>
            <div className="col-md-2 d-flex gap-2">
              <button type="submit" className="btn btn-success flex-grow-1" disabled={creating}>
                {creating ? "..." : "Crear"}
              </button>
            </div>
          </form>
        </div>
      )}

      {listError && <div className="alert alert-danger">{listError}</div>}

      {loading ? (
        <p>Cargando...</p>
      ) : users.length === 0 ? (
        <div className="sn-empty-state">
          <i className="bi bi-people sn-empty-icon" />
          <p className="mb-0">No hay usuarios registrados.</p>
        </div>
      ) : (
        <div className="sn-card p-3">
          <table className="table align-middle mb-0">
            <thead>
              <tr>
                <th>Usuario</th>
                <th>Rol</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => {
                const isAdminRow = u.role === "admin";
                const busy = Boolean(rowBusy[u.id]);
                return (
                  <tr key={u.id}>
                    <td>{u.username}</td>
                    <td>
                      <span className={`badge sn-badge-${u.role}`}>{ROLE_LABEL[u.role] || u.role}</span>
                    </td>
                    <td>
                      {u.is_active ? (
                        <span className="badge bg-success">Activo</span>
                      ) : (
                        <span className="badge bg-secondary">Inactivo</span>
                      )}
                      {u.locked && <span className="badge bg-danger ms-1">Bloqueado</span>}
                    </td>
                    <td>
                      {isAdminRow ? (
                        <span className="text-muted small">Sin acciones (admin)</span>
                      ) : (
                        <div className="d-flex flex-wrap align-items-center gap-2">
                          <button
                            type="button"
                            className="btn btn-sm btn-outline-primary"
                            disabled={busy}
                            onClick={() => handleToggleActive(u)}
                          >
                            {u.is_active ? "Desactivar" : "Activar"}
                          </button>
                          <select
                            className="form-select form-select-sm"
                            style={{ width: "auto" }}
                            value={roleDrafts[u.id] ?? u.role}
                            onChange={(e) =>
                              setRoleDrafts((prev) => ({ ...prev, [u.id]: e.target.value }))
                            }
                          >
                            <option value="editor">Editor</option>
                            <option value="lector">Lector</option>
                          </select>
                          <button
                            type="button"
                            className="btn btn-sm btn-outline-secondary"
                            disabled={busy || (roleDrafts[u.id] ?? u.role) === u.role}
                            onClick={() => handleRoleChange(u)}
                          >
                            Cambiar rol
                          </button>
                        </div>
                      )}
                      {rowError[u.id] && (
                        <div className="text-danger small mt-1">{rowError[u.id]}</div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Layout>
  );
}
