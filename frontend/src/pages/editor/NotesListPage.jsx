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

function formatDate(value) {
  if (!value) return "";
  try {
    return new Date(value).toLocaleString();
  } catch (err) {
    return value;
  }
}

export default function NotesListPage() {
  const [notes, setNotes] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState("");
  const [busyId, setBusyId] = useState(null);

  async function fetchAll() {
    setLoading(true);
    setListError("");
    try {
      const [notesResp, categoriesResp] = await Promise.all([
        apiClient.get("notes/"),
        apiClient.get("categories/"),
      ]);
      const notesData = notesResp.data;
      const categoriesData = categoriesResp.data;
      setNotes(Array.isArray(notesData) ? notesData : notesData.results || []);
      setCategories(Array.isArray(categoriesData) ? categoriesData : categoriesData.results || []);
    } catch (err) {
      setListError(extractError(err, "No se pudo cargar la lista de notas."));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchAll();
  }, []);

  const categoryName = (id) => categories.find((c) => c.id === id)?.name;

  async function handleDelete(note) {
    if (!window.confirm(`¿Eliminar la nota "${note.title}"?`)) return;
    setBusyId(note.id);
    setListError("");
    try {
      await apiClient.delete(`notes/${note.id}/`);
      await fetchAll();
    } catch (err) {
      setListError(extractError(err, "No se pudo eliminar la nota."));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <Layout>
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h1 className="h3 mb-0">Mis notas</h1>
        <Link to="/notes/new" className="btn btn-primary">
          <i className="bi bi-file-earmark-plus" /> Nueva nota
        </Link>
      </div>

      {listError && <div className="alert alert-danger">{listError}</div>}

      {loading ? (
        <p>Cargando...</p>
      ) : notes.length === 0 ? (
        <div className="sn-empty-state">
          <i className="bi bi-journal-text sn-empty-icon" />
          <p className="mb-0">No tienes notas todavía.</p>
        </div>
      ) : (
        <div className="row row-cols-1 row-cols-md-3 g-3">
          {notes.map((note) => (
            <div className="col" key={note.id}>
              <div className="sn-card p-3 h-100 d-flex flex-column">
                <h2 className="card-title h6">{note.title}</h2>
                <div className="mb-2">
                  {note.category ? (
                    <span className="badge bg-secondary">{categoryName(note.category) || "Categoría"}</span>
                  ) : (
                    <span className="badge bg-light text-dark">Sin categoría</span>
                  )}
                </div>
                <p className="text-muted small mb-3">Actualizada: {formatDate(note.updated_at)}</p>
                <div className="sn-card-actions mt-auto d-flex gap-2">
                  <Link to={`/notes/${note.id}`} className="btn btn-sm btn-outline-primary flex-grow-1">
                    Ver
                  </Link>
                  <Link to={`/notes/${note.id}/edit`} className="btn btn-sm btn-outline-secondary">
                    Editar
                  </Link>
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-danger"
                    disabled={busyId === note.id}
                    onClick={() => handleDelete(note)}
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
