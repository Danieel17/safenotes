import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
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

export default function NoteFormPage() {
  const { id } = useParams();
  const isEdit = Boolean(id);
  const navigate = useNavigate();

  const [categories, setCategories] = useState([]);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [category, setCategory] = useState("");
  const [loading, setLoading] = useState(isEdit);
  const [loadError, setLoadError] = useState("");
  const [saveError, setSaveError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const categoriesResp = await apiClient.get("categories/");
        const categoriesData = categoriesResp.data;
        setCategories(Array.isArray(categoriesData) ? categoriesData : categoriesData.results || []);

        if (isEdit) {
          const { data } = await apiClient.get(`notes/${id}/`);
          setTitle(data.title || "");
          setContent(data.content || "");
          setCategory(data.category ?? "");
        }
      } catch (err) {
        setLoadError(extractError(err, "No se pudo cargar la nota."));
      } finally {
        setLoading(false);
      }
    }
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function handleSubmit(e) {
    e.preventDefault();
    setSaveError("");
    setSaving(true);
    const payload = {
      title,
      content,
      category: category === "" ? null : Number(category),
    };
    try {
      if (isEdit) {
        const { data } = await apiClient.patch(`notes/${id}/`, payload);
        navigate(`/notes/${data.id}`);
      } else {
        const { data } = await apiClient.post("notes/", payload);
        navigate(`/notes/${data.id}`);
      }
    } catch (err) {
      setSaveError(extractError(err, "No se pudo guardar la nota."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Layout>
      <h1 className="h3 mb-3">{isEdit ? "Editar nota" : "Nueva nota"}</h1>

      {loading ? (
        <p>Cargando...</p>
      ) : loadError ? (
        <div className="alert alert-danger">{loadError}</div>
      ) : (
        <div className="sn-card p-3" style={{ maxWidth: 640 }}>
          {saveError && <div className="alert alert-danger py-2">{saveError}</div>}
          <form onSubmit={handleSubmit}>
            <div className="mb-3">
              <label className="form-label">Título</label>
              <input
                className="form-control"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>
            <div className="mb-3">
              <label className="form-label">Contenido</label>
              <textarea
                className="form-control"
                rows={8}
                value={content}
                onChange={(e) => setContent(e.target.value)}
              />
            </div>
            <div className="mb-3">
              <label className="form-label">Categoría</label>
              <select
                className="form-select"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                <option value="">Sin categoría</option>
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="d-flex gap-2">
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? "Guardando..." : "Guardar"}
              </button>
              <button
                type="button"
                className="btn btn-outline-secondary"
                onClick={() => navigate(-1)}
              >
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}
    </Layout>
  );
}
