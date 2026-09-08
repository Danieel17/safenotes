import { useEffect, useState } from "react";
import Layout from "../../components/Layout";
import apiClient from "../../api/client";

export default function AuditLogPage() {
  const [entries, setEntries] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [hasNext, setHasNext] = useState(false);
  const [hasPrevious, setHasPrevious] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [actionFilter, setActionFilter] = useState("");
  const [actorFilter, setActorFilter] = useState("");

  async function fetchLog(targetPage) {
    setLoading(true);
    setError("");
    try {
      const params = { page: targetPage };
      if (actionFilter) params.action = actionFilter;
      if (actorFilter) params.actor = actorFilter;
      const { data } = await apiClient.get("audit-log/", { params });
      const results = Array.isArray(data) ? data : data.results || [];
      setEntries(results);
      setCount(Array.isArray(data) ? results.length : data.count || 0);
      setHasNext(Boolean(!Array.isArray(data) && data.next));
      setHasPrevious(Boolean(!Array.isArray(data) && data.previous));
    } catch (err) {
      setError(err?.response?.data?.detail || "No se pudo cargar el registro de auditoría.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchLog(1);
    setPage(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleFilterSubmit(e) {
    e.preventDefault();
    setPage(1);
    fetchLog(1);
  }

  function goToPage(next) {
    setPage(next);
    fetchLog(next);
  }

  return (
    <Layout>
      <h1 className="h3 mb-3">Registro de auditoría</h1>

      <form onSubmit={handleFilterSubmit} className="row g-2 align-items-end mb-3">
        <div className="col-md-3">
          <label className="form-label">Acción</label>
          <input
            className="form-control"
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            placeholder="p.ej. user_created"
          />
        </div>
        <div className="col-md-3">
          <label className="form-label">Actor</label>
          <input
            className="form-control"
            value={actorFilter}
            onChange={(e) => setActorFilter(e.target.value)}
            placeholder="nombre de usuario"
          />
        </div>
        <div className="col-md-2">
          <button type="submit" className="btn btn-primary w-100">
            Filtrar
          </button>
        </div>
      </form>

      {error && <div className="alert alert-danger">{error}</div>}

      {loading ? (
        <p>Cargando...</p>
      ) : entries.length === 0 ? (
        <div className="sn-empty-state">
          <i className="bi bi-journal-text sn-empty-icon" />
          <p className="mb-0">No hay eventos registrados.</p>
        </div>
      ) : (
        <>
          <div className="sn-card p-3">
            <table className="table align-middle mb-0">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Actor</th>
                  <th>Acción</th>
                  <th>Detalle</th>
                  <th>IP</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <tr key={entry.id}>
                    <td>{new Date(entry.timestamp).toLocaleString()}</td>
                    <td>{entry.actor || "—"}</td>
                    <td>{entry.action}</td>
                    <td>{entry.target_repr}</td>
                    <td>{entry.ip_address || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="d-flex justify-content-between align-items-center mt-3">
            <span className="text-muted small">
              Página {page} · {count} eventos en total
            </span>
            <div className="d-flex gap-2">
              <button
                type="button"
                className="btn btn-sm btn-outline-secondary"
                disabled={!hasPrevious || loading}
                onClick={() => goToPage(page - 1)}
              >
                Anterior
              </button>
              <button
                type="button"
                className="btn btn-sm btn-outline-secondary"
                disabled={!hasNext || loading}
                onClick={() => goToPage(page + 1)}
              >
                Siguiente
              </button>
            </div>
          </div>
        </>
      )}
    </Layout>
  );
}
