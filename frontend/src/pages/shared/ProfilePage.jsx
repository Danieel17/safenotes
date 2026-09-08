import { useEffect, useState } from "react";
import Layout from "../../components/Layout";
import apiClient from "../../api/client";

const ROLE_LABEL = {
  admin: "Administrador",
  editor: "Editor",
  lector: "Lector",
};

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

export default function ProfilePage() {
  const [profile, setProfile] = useState(null);
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [saveError, setSaveError] = useState("");
  const [saveSuccess, setSaveSuccess] = useState("");
  const [saving, setSaving] = useState(false);

  async function fetchProfile() {
    setLoading(true);
    setLoadError("");
    try {
      const { data } = await apiClient.get("profile/");
      setProfile(data);
      setEmail(data.email || "");
    } catch (err) {
      setLoadError(extractError(err, "No se pudo cargar el perfil."));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchProfile();
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setSaveError("");
    setSaveSuccess("");
    setSaving(true);
    try {
      const { data } = await apiClient.patch("profile/", { email });
      setProfile(data);
      setEmail(data.email || "");
      setSaveSuccess("Perfil actualizado correctamente.");
    } catch (err) {
      setSaveError(extractError(err, "No se pudo actualizar el perfil."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Layout>
      <h1 className="h3 mb-3">Mi perfil</h1>

      {loading ? (
        <p>Cargando...</p>
      ) : loadError ? (
        <div className="alert alert-danger">{loadError}</div>
      ) : (
        <div className="sn-card p-3" style={{ maxWidth: 480 }}>
          <div className="mb-3">
            <label className="form-label">Usuario</label>
            <input className="form-control" value={profile?.username || ""} disabled readOnly />
          </div>
          <div className="mb-3">
            <label className="form-label">Rol</label>
            <div>
              <span className={`badge sn-badge-${profile?.role}`}>
                {ROLE_LABEL[profile?.role] || profile?.role}
              </span>
            </div>
          </div>

          {saveError && <div className="alert alert-danger py-2">{saveError}</div>}
          {saveSuccess && <div className="alert alert-success py-2">{saveSuccess}</div>}

          <form onSubmit={handleSubmit}>
            <div className="mb-3">
              <label className="form-label">Correo electrónico</label>
              <input
                type="email"
                className="form-control"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? "Guardando..." : "Guardar cambios"}
            </button>
          </form>
        </div>
      )}
    </Layout>
  );
}
