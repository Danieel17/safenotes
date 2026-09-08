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

export default function SharedNotesPage() {
  const [shares, setShares] = useState([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState("");

  async function fetchShares() {
    setLoading(true);
    setListError("");
    try {
      const { data } = await apiClient.get("shared-notes/");
      setShares(Array.isArray(data) ? data : data.results || []);
    } catch (err) {
      setListError(extractError(err, "No se pudo cargar las notas compartidas."));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchShares();
  }, []);

  return (
    <Layout>
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h1 className="h3 mb-0">Notas compartidas conmigo</h1>
      </div>

      {listError && <div className="alert alert-danger">{listError}</div>}

      {loading ? (
        <p>Cargando...</p>
      ) : shares.length === 0 ? (
        <div className="sn-empty-state">
          <i className="bi bi-journal-text sn-empty-icon" />
          <p className="mb-0">Todavía no tienes notas compartidas.</p>
        </div>
      ) : (
        <div className="row row-cols-1 row-cols-md-3 g-3">
          {shares.map((share) => (
            <div className="col" key={share.id}>
              <div className="sn-card p-3 h-100 d-flex flex-column">
                <h2 className="card-title h6">{share.note_title}</h2>
                <div className="mb-2">
                  {share.note_category ? (
                    <span className="badge bg-secondary">{share.note_category}</span>
                  ) : (
                    <span className="badge bg-light text-dark">Sin categoría</span>
                  )}
                </div>
                <p className="text-muted small mb-3">Compartida por: {share.owner_username}</p>
                <div className="sn-card-actions mt-auto d-flex gap-2">
                  <Link to={`/shared/${share.id}`} className="btn btn-sm btn-outline-primary flex-grow-1">
                    Ver
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </Layout>
  );
}
