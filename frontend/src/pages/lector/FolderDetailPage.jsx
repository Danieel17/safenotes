import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
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

export default function FolderDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [folder, setFolder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [deleting, setDeleting] = useState(false);

  const [renameValue, setRenameValue] = useState("");
  const [renaming, setRenaming] = useState(false);
  const [renameError, setRenameError] = useState("");

  async function fetchFolder() {
    setLoading(true);
    setLoadError("");
    try {
      const { data } = await apiClient.get(`folders/${id}/`);
      setFolder(data);
      setRenameValue(data.name);
    } catch (err) {
      setLoadError(extractError(err, "No se pudo cargar la carpeta."));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchFolder();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function handleRename(e) {
    e.preventDefault();
    setRenameError("");
    setRenaming(true);
    try {
      await apiClient.patch(`folders/${id}/`, { name: renameValue.trim() });
      await fetchFolder();
    } catch (err) {
      setRenameError(extractError(err, "No se pudo renombrar la carpeta."));
    } finally {
      setRenaming(false);
    }
  }

  async function handleDelete() {
    if (!folder || !window.confirm(`¿Eliminar la carpeta "${folder.name}"?`)) return;
    setDeleting(true);
    setLoadError("");
    try {
      await apiClient.delete(`folders/${id}/`);
      navigate("/folders");
    } catch (err) {
      setLoadError(extractError(err, "No se pudo eliminar la carpeta."));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Layout>
      {loading ? (
        <p>Cargando...</p>
      ) : loadError && !folder ? (
        <div className="alert alert-danger">{loadError}</div>
      ) : folder ? (
        <>
          <div className="d-flex justify-content-between align-items-start mb-3">
            <h1 className="h3 mb-0">{folder.name}</h1>
            <button type="button" className="btn btn-outline-danger" disabled={deleting} onClick={handleDelete}>
              Eliminar
            </button>
          </div>

          {loadError && <div className="alert alert-danger">{loadError}</div>}

          <div className="sn-card p-3 mb-4" style={{ maxWidth: 480 }}>
            <h2 className="h6">Renombrar</h2>
            {renameError && <div className="alert alert-danger py-2">{renameError}</div>}
            <form onSubmit={handleRename} className="row g-2 align-items-end">
              <div className="col-md-8">
                <label className="form-label">Nombre</label>
                <input
                  className="form-control"
                  required
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                />
              </div>
              <div className="col-md-4">
                <button type="submit" className="btn btn-primary w-100" disabled={renaming}>
                  {renaming ? "..." : "Guardar"}
                </button>
              </div>
            </form>
          </div>

          <div className="sn-card p-3">
            <h2 className="h6">Notas en esta carpeta</h2>
            {Array.isArray(folder.items) && folder.items.length > 0 ? (
              <ul className="list-group">
                {folder.items.map((item) => (
                  <li
                    key={item.folder_item_id}
                    className="list-group-item d-flex justify-content-between align-items-center"
                  >
                    {item.note_title}
                    <Link to={`/shared/${item.share_id}`} className="btn btn-sm btn-outline-primary">
                      Ver
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-muted small mb-0">Esta carpeta no tiene notas todavía.</p>
            )}
          </div>
        </>
      ) : null}
    </Layout>
  );
}
