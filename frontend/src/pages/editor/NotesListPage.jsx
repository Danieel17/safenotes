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
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");

  async function fetchCategories() {
    try {
      const { data } = await apiClient.get("categories/");
      setCategories(Array.isArray(data) ? data : data.results || []);
    } catch (err) {
      // La lista de categorías es secundaria; un fallo aquí no debe bloquear
      // la vista de notas, solo deshabilita el filtro por categoría.
    }
  }

  async function fetchNotes() {
    setLoading(true);
    setListError("");
    try {
      const params = {};
      if (search.trim()) params.search = search.trim();
      if (categoryFilter) params.category = categoryFilter;
      const { data } = await apiClient.get("notes/", { params });
      setNotes(Array.isArray(data) ? data : data.results || []);
    } catch (err) {
      setListError(extractError(err, "No se pudo cargar la lista de notas."));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchCategories();
  }, []);

  useEffect(() => {
    const timeoutId = setTimeout(fetchNotes, 300);
    return () => clearTimeout(timeoutId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, categoryFilter]);

  const categoryName = (id) => categories.find((c) => c.id === id)?.name;

  async function handleDelete(note) {
    if (!window.confirm(`¿Eliminar la nota "${note.title}"?`)) return;
    setBusyId(note.id);
    setListError("");
    try {
      await apiClient.delete(`notes/${note.id}/`);
      await fetchNotes();
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

      <div className="row g-2 mb-3">
        <div className="col-sm-7">
          <input
            type="search"
            className="form-control"
            placeholder="Buscar por título..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="col-sm-5">
          <select
            className="form-select"
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
          >
            <option value="">Todas las categorías</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {listError && <div className="alert alert-danger">{listError}</div>}

      {loading ? (
        <p>Cargando...</p>
      ) : notes.length === 0 ? (
        <div className="sn-empty-state">
          <i className="bi bi-journal-text sn-empty-icon" />
          <p className="mb-0">
            {search || categoryFilter
              ? "No hay notas que coincidan con el filtro."
              : "No tienes notas todavía."}
          </p>
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
