import { useEffect, useState } from "react";
import Layout from "../../components/Layout";
import apiClient from "../../api/client";

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

export default function CategoriesPage() {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState("");

  const [newName, setNewName] = useState("");
  const [createError, setCreateError] = useState("");
  const [creating, setCreating] = useState(false);

  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState("");
  const [editError, setEditError] = useState("");
  const [busyId, setBusyId] = useState(null);

  async function fetchCategories() {
    setLoading(true);
    setListError("");
    try {
      const { data } = await apiClient.get("categories/");
      const results = Array.isArray(data) ? data : data.results || [];
      setCategories(results);
    } catch (err) {
      setListError(extractError(err, "No se pudo cargar las categorías."));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchCategories();
  }, []);

  async function handleCreate(e) {
    e.preventDefault();
    setCreateError("");
    setCreating(true);
    try {
      await apiClient.post("categories/", { name: newName });
      setNewName("");
      await fetchCategories();
    } catch (err) {
      setCreateError(extractError(err, "No se pudo crear la categoría."));
    } finally {
      setCreating(false);
    }
  }

  function startEdit(cat) {
    setEditingId(cat.id);
    setEditName(cat.name);
    setEditError("");
  }

  async function handleSaveEdit(cat) {
    setEditError("");
    setBusyId(cat.id);
    try {
      await apiClient.patch(`categories/${cat.id}/`, { name: editName });
      setEditingId(null);
      await fetchCategories();
    } catch (err) {
      setEditError(extractError(err, "No se pudo actualizar la categoría."));
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(cat) {
    if (!window.confirm(`¿Eliminar la categoría "${cat.name}"?`)) return;
    setBusyId(cat.id);
    setListError("");
    try {
      await apiClient.delete(`categories/${cat.id}/`);
      await fetchCategories();
    } catch (err) {
      setListError(extractError(err, "No se pudo eliminar la categoría."));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <Layout>
      <h1 className="h3 mb-3">Categorías</h1>

      <div className="sn-card p-3 mb-4">
        <h2 className="h6">Nueva categoría</h2>
        {createError && <div className="alert alert-danger py-2">{createError}</div>}
        <form onSubmit={handleCreate} className="row g-2 align-items-end">
          <div className="col-md-6">
            <input
              className="form-control"
              placeholder="Nombre de la categoría"
              required
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
          </div>
          <div className="col-md-2">
            <button type="submit" className="btn btn-success w-100" disabled={creating}>
              {creating ? "..." : "Crear"}
            </button>
          </div>
        </form>
      </div>

      {listError && <div className="alert alert-danger">{listError}</div>}

      {loading ? (
        <p>Cargando...</p>
      ) : categories.length === 0 ? (
        <div className="sn-empty-state">
          <i className="bi bi-tags sn-empty-icon" />
          <p className="mb-0">No hay categorías registradas.</p>
        </div>
      ) : (
        <div className="sn-card p-3">
          <table className="table align-middle mb-0">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Creada por</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {categories.map((cat) => (
                <tr key={cat.id}>
                  <td>
                    {editingId === cat.id ? (
                      <input
                        className="form-control form-control-sm"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                      />
                    ) : (
                      cat.name
                    )}
                    {editingId === cat.id && editError && (
                      <div className="text-danger small mt-1">{editError}</div>
                    )}
                  </td>
                  <td>{cat.created_by}</td>
                  <td>
                    {editingId === cat.id ? (
                      <div className="d-flex gap-2">
                        <button
                          type="button"
                          className="btn btn-sm btn-success"
                          disabled={busyId === cat.id}
                          onClick={() => handleSaveEdit(cat)}
                        >
                          Guardar
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-secondary"
                          onClick={() => setEditingId(null)}
                        >
                          Cancelar
                        </button>
                      </div>
                    ) : (
                      <div className="d-flex gap-2">
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-primary"
                          onClick={() => startEdit(cat)}
                        >
                          Editar
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-danger"
                          disabled={busyId === cat.id}
                          onClick={() => handleDelete(cat)}
                        >
                          Eliminar
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Layout>
  );
}
