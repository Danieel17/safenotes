import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
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

function formatDate(value) {
  if (!value) return "";
  try {
    return new Date(value).toLocaleString();
  } catch (err) {
    return value;
  }
}

export default function SharedNoteDetailPage() {
  const { shareId } = useParams();

  const [share, setShare] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  const [folders, setFolders] = useState([]);
  const [selectedFolder, setSelectedFolder] = useState("");
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState("");
  const [addSuccess, setAddSuccess] = useState("");

  async function fetchShare() {
    setLoading(true);
    setLoadError("");
    try {
      const { data } = await apiClient.get(`shared-notes/${shareId}/`);
      setShare(data);
    } catch (err) {
      setLoadError(extractError(err, "No se pudo cargar la nota compartida."));
    } finally {
      setLoading(false);
    }
  }

  async function fetchFolders() {
    try {
      const { data } = await apiClient.get("folders/");
      const list = Array.isArray(data) ? data : data.results || [];
      setFolders(list);
      if (list.length > 0) {
        setSelectedFolder(String(list[0].id));
      }
    } catch (err) {
      // Non-fatal: folder select will just be empty.
    }
  }

  useEffect(() => {
    fetchShare();
    fetchFolders();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shareId]);

  async function handleAddToFolder(e) {
    e.preventDefault();
    if (!selectedFolder) return;
    setAdding(true);
    setAddError("");
    setAddSuccess("");
    try {
      const { data } = await apiClient.post(`shared-notes/${shareId}/add-to-folder/`, {
        folder_id: Number(selectedFolder),
      });
      setAddSuccess(data?.detail || "Nota agregada a la carpeta.");
    } catch (err) {
      setAddError(extractError(err, "No se pudo agregar la nota a la carpeta."));
    } finally {
      setAdding(false);
    }
  }

  return (
    <Layout>
      {loading ? (
        <p>Cargando...</p>
      ) : loadError && !share ? (
        <div className="alert alert-danger">{loadError}</div>
      ) : share ? (
        <>
          <div className="d-flex justify-content-between align-items-start mb-3">
            <h1 className="h3 mb-0">{share.note_title}</h1>
          </div>

          {loadError && <div className="alert alert-danger">{loadError}</div>}

          <div className="sn-card p-3 mb-4">
            <div className="mb-2">
              {share.note_category ? (
                <span className="badge bg-secondary">{share.note_category}</span>
              ) : (
                <span className="badge bg-light text-dark">Sin categoría</span>
              )}
            </div>
            <p style={{ whiteSpace: "pre-wrap" }}>{share.note_content}</p>
            <p className="text-muted small mb-0">
              Compartida por: {share.owner_username} · {formatDate(share.created_at)}
            </p>
          </div>

          <div className="sn-card p-3" style={{ maxWidth: 480 }}>
            <h2 className="h6">Agregar a carpeta</h2>
            {addError && <div className="alert alert-danger py-2">{addError}</div>}
            {addSuccess && <div className="alert alert-success py-2">{addSuccess}</div>}
            {folders.length === 0 ? (
              <p className="text-muted small mb-0">
                No tienes carpetas todavía. Crea una en la sección de Carpetas.
              </p>
            ) : (
              <form onSubmit={handleAddToFolder} className="row g-2 align-items-end">
                <div className="col-md-8">
                  <label className="form-label">Carpeta</label>
                  <select
                    className="form-select"
                    value={selectedFolder}
                    onChange={(e) => setSelectedFolder(e.target.value)}
                  >
                    {folders.map((folder) => (
                      <option key={folder.id} value={folder.id}>
                        {folder.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="col-md-4">
                  <button type="submit" className="btn btn-primary w-100" disabled={adding}>
                    {adding ? "..." : "Agregar"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </>
      ) : null}
    </Layout>
  );
}
