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

function formatDate(value) {
  if (!value) return "";
  try {
    return new Date(value).toLocaleString();
  } catch (err) {
    return value;
  }
}

export default function NoteDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [note, setNote] = useState(null);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [deleting, setDeleting] = useState(false);

  const [shareUsername, setShareUsername] = useState("");
  const [shareError, setShareError] = useState("");
  const [sharing, setSharing] = useState(false);
  const [unshareBusyId, setUnshareBusyId] = useState(null);
  const [unshareError, setUnshareError] = useState("");

  async function fetchNote() {
    setLoading(true);
    setLoadError("");
    try {
      const [noteResp, categoriesResp] = await Promise.all([
        apiClient.get(`notes/${id}/`),
        apiClient.get("categories/"),
      ]);
      setNote(noteResp.data);
      const categoriesData = categoriesResp.data;
      setCategories(Array.isArray(categoriesData) ? categoriesData : categoriesData.results || []);
    } catch (err) {
      setLoadError(extractError(err, "No se pudo cargar la nota."));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchNote();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const categoryName = note?.category
    ? categories.find((c) => c.id === note.category)?.name
    : null;

  async function handleDelete() {
    if (!note || !window.confirm(`¿Eliminar la nota "${note.title}"?`)) return;
    setDeleting(true);
    setLoadError("");
    try {
      await apiClient.delete(`notes/${id}/`);
      navigate("/notes");
    } catch (err) {
      setLoadError(extractError(err, "No se pudo eliminar la nota."));
    } finally {
      setDeleting(false);
    }
  }

  async function handleShare(e) {
    e.preventDefault();
    setShareError("");
    setSharing(true);
    try {
      await apiClient.post(`notes/${id}/share/`, {
        shared_with_username: shareUsername.trim(),
      });
      setShareUsername("");
      await fetchNote();
    } catch (err) {
      setShareError(extractError(err, "No se pudo compartir la nota."));
    } finally {
      setSharing(false);
    }
  }

  async function handleUnshare(share) {
    setUnshareError("");
    setUnshareBusyId(share.id);
    try {
      await apiClient.post(`notes/${id}/unshare/`, { shared_with: share.shared_with });
      await fetchNote();
    } catch (err) {
      setUnshareError(extractError(err, "No se pudo dejar de compartir."));
    } finally {
      setUnshareBusyId(null);
    }
  }

  return (
    <Layout>
      {loading ? (
        <p>Cargando...</p>
      ) : loadError && !note ? (
        <div className="alert alert-danger">{loadError}</div>
      ) : note ? (
        <>
          <div className="d-flex justify-content-between align-items-start mb-3">
            <h1 className="h3 mb-0">{note.title}</h1>
            <div className="d-flex gap-2">
              <Link to={`/notes/${note.id}/edit`} className="btn btn-outline-secondary">
                Editar
              </Link>
              <button
                type="button"
                className="btn btn-outline-danger"
                disabled={deleting}
                onClick={handleDelete}
              >
                Eliminar
              </button>
            </div>
          </div>

          {loadError && <div className="alert alert-danger">{loadError}</div>}

          <div className="sn-card p-3 mb-4">
            <div className="mb-2">
              {categoryName ? (
                <span className="badge bg-secondary">{categoryName}</span>
              ) : (
                <span className="badge bg-light text-dark">Sin categoría</span>
              )}
            </div>
            <p style={{ whiteSpace: "pre-wrap" }}>{note.content}</p>
            <p className="text-muted small mb-0">Actualizada: {formatDate(note.updated_at)}</p>
          </div>

          <div className="sn-card p-3" style={{ maxWidth: 640 }}>
            <h2 className="h6">Compartir</h2>
            {shareError && <div className="alert alert-danger py-2">{shareError}</div>}
            <form onSubmit={handleShare} className="row g-2 align-items-end mb-3">
              <div className="col-md-8">
                <label className="form-label">Usuario lector</label>
                <input
                  className="form-control"
                  placeholder="username del lector"
                  required
                  value={shareUsername}
                  onChange={(e) => setShareUsername(e.target.value)}
                />
              </div>
              <div className="col-md-4">
                <button type="submit" className="btn btn-primary w-100" disabled={sharing}>
                  {sharing ? "..." : "Compartir"}
                </button>
              </div>
            </form>

            {unshareError && <div className="alert alert-danger py-2">{unshareError}</div>}

            {note.shares && note.shares.length > 0 ? (
              <ul className="list-group">
                {note.shares.map((share) => (
                  <li
                    key={share.id}
                    className="list-group-item d-flex justify-content-between align-items-center"
                  >
                    {share.shared_with_username}
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-danger"
                      disabled={unshareBusyId === share.id}
                      onClick={() => handleUnshare(share)}
                    >
                      Dejar de compartir
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-muted small mb-0">Esta nota no está compartida con nadie.</p>
            )}
          </div>
        </>
      ) : null}
    </Layout>
  );
}
