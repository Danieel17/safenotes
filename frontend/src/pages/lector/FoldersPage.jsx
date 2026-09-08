import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
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

export default function FoldersPage() {
  const [folders, setFolders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState("");
  const [busyId, setBusyId] = useState(null);

  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");

  async function fetchFolders() {
    setLoading(true);
    setListError("");
    try {
      const { data } = await apiClient.get("folders/");
      setFolders(Array.isArray(data) ? data : data.results || []);
    } catch (err) {
      setListError(extractError(err, "No se pudo cargar las carpetas."));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchFolders();
  }, []);

  async function handleCreate(e) {
    e.preventDefault();
    setCreateError("");
    setCreating(true);
    try {
      await apiClient.post("folders/", { name: newName.trim() });
      setNewName("");
      await fetchFolders();
    } catch (err) {
      setCreateError(extractError(err, "No se pudo crear la carpeta."));
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(folder) {
    if (!window.confirm(`¿Eliminar la carpeta "${folder.name}"?`)) return;
    setBusyId(folder.id);
    setListError("");
    try {
      await apiClient.delete(`folders/${folder.id}/`);
      await fetchFolders();
    } catch (err) {
      setListError(extractError(err, "No se pudo eliminar la carpeta."));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <Layout>
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h1 className="h3 mb-0">Mis carpetas</h1>
      </div>

      <div className="sn-card p-3 mb-4" style={{ maxWidth: 480 }}>
        <h2 className="h6">Nueva carpeta</h2>
        {createError && <div className="alert alert-danger py-2">{createError}</div>}
        <form onSubmit={handleCreate} className="row g-2 align-items-end">
          <div className="col-md-8">
            <label className="form-label">Nombre</label>
            <input
              className="form-control"
              required
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
          </div>
          <div className="col-md-4">
            <button type="submit" className="btn btn-primary w-100" disabled={creating}>
              {creating ? "..." : "Crear"}
            </button>
          </div>
        </form>
      </div>

      {listError && <div className="alert alert-danger">{listError}</div>}

      {loading ? (
        <p>Cargando...</p>
      ) : folders.length === 0 ? (
        <div className="sn-empty-state">
          <i className="bi bi-folder2 sn-empty-icon" />
          <p className="mb-0">Todavía no tienes carpetas.</p>
        </div>
      ) : (
        <div className="row row-cols-1 row-cols-md-3 g-3">
          {folders.map((folder) => (
            <div className="col" key={folder.id}>
              <div className="sn-card p-3 h-100 d-flex flex-column">
                <h2 className="card-title h6">{folder.name}</h2>
                {Array.isArray(folder.items) && (
                  <p className="text-muted small mb-3">{folder.items.length} nota(s)</p>
                )}
                <div className="sn-card-actions mt-auto d-flex gap-2">
                  <Link to={`/folders/${folder.id}`} className="btn btn-sm btn-outline-primary flex-grow-1">
                    Ver
                  </Link>
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-danger"
                    disabled={busyId === folder.id}
                    onClick={() => handleDelete(folder)}
                  >
                    Eliminar
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </Layout>
  );
}
