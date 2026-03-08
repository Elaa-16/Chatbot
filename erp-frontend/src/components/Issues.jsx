import { useState, useEffect, useCallback } from "react";
import api from "../services/api";

const SEVERITY_CONFIG = {
  Critical: { color: "#ef4444", bg: "#fef2f2", border: "#fecaca", dot: "#ef4444" },
  High:     { color: "#f97316", bg: "#fff7ed", border: "#fed7aa", dot: "#f97316" },
  Medium:   { color: "#eab308", bg: "#fefce8", border: "#fef08a", dot: "#eab308" },
  Low:      { color: "#22c55e", bg: "#f0fdf4", border: "#bbf7d0", dot: "#22c55e" },
};

const CATEGORY_CONFIG = {
  Safety:    { icon: "🦺", color: "#ef4444", bg: "#fef2f2" },
  Quality:   { icon: "✅", color: "#8b5cf6", bg: "#f5f3ff" },
  Delay:     { icon: "⏱️", color: "#f97316", bg: "#fff7ed" },
  Budget:    { icon: "💰", color: "#10b981", bg: "#f0fdf4" },
  Technical: { icon: "⚙️", color: "#3b82f6", bg: "#eff6ff" },
  Other:     { icon: "📋", color: "#6b7280", bg: "#f9fafb" },
};

const STATUS_COLUMNS = [
  { key: "Open",        label: "Ouvert",      icon: "🔴", color: "#ef4444" },
  { key: "In Progress", label: "En cours",    icon: "🟡", color: "#f97316" },
  { key: "Resolved",    label: "Résolu",      icon: "🟢", color: "#22c55e" },
  { key: "Closed",      label: "Clôturé",     icon: "⚫", color: "#6b7280" },
];

const formatDate = (d) => d ? new Date(d).toLocaleDateString("fr-FR") : "—";

export default function Issues() {
  const [issues, setIssues]       = useState([]);
  const [projects, setProjects]   = useState([]);
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading]     = useState(true);
  const [search, setSearch]       = useState("");
  const [filterSeverity, setFilterSeverity] = useState("");
  const [filterCategory, setFilterCategory] = useState("");
  const [filterProject, setFilterProject]   = useState("");
  const [showModal, setShowModal] = useState(false);
  const [editIssue, setEditIssue] = useState(null);
  const [form, setForm] = useState({
    issue_id: "", project_id: "", title: "", description: "",
    severity: "Medium", category: "Safety", status: "Open", assigned_to: "",
  });

  const userRole = localStorage.getItem("user_role");
  const canEdit  = userRole === "ceo" || userRole === "manager";

  const fetchAll = useCallback(async () => {
    try {
      setLoading(true);
      const [issRes, projRes, empRes] = await Promise.all([
        api.get("/issues"),
        api.get("/projects"),
        api.get("/employees"),
      ]);
      setIssues(issRes.data);
      setProjects(projRes.data);
      setEmployees(empRes.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const filtered = issues.filter(i => {
    const q = search.toLowerCase();
    const matchSearch = !q || i.title?.toLowerCase().includes(q) || i.description?.toLowerCase().includes(q);
    const matchSev  = !filterSeverity || i.severity === filterSeverity;
    const matchCat  = !filterCategory || i.category === filterCategory;
    const matchProj = !filterProject  || i.project_id === filterProject;
    return matchSearch && matchSev && matchCat && matchProj;
  });

  const byStatus = (status) => filtered.filter(i => i.status === status);

  const openCreate = () => {
    setEditIssue(null);
    setForm({ issue_id: `IS${Date.now()}`, project_id: "", title: "", description: "", severity: "Medium", category: "Safety", status: "Open", assigned_to: "" });
    setShowModal(true);
  };

  const openEdit = (issue) => {
    setEditIssue(issue);
    setForm({ ...issue });
    setShowModal(true);
  };

  const handleSave = async () => {
    try {
      if (editIssue) {
        await api.put(`/issues/${form.issue_id}`, form);
      } else {
        await api.post("/issues", { ...form, reported_by: localStorage.getItem("user_id") });
      }
      setShowModal(false);
      fetchAll();
    } catch (e) {
      console.error(e);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Supprimer cet incident ?")) return;
    try {
      await api.delete(`/issues/${id}`);
      fetchAll();
    } catch (e) {
      console.error(e);
    }
  };

  const handleStatusChange = async (issue, newStatus) => {
    try {
      await api.put(`/issues/${issue.issue_id}`, { status: newStatus });
      fetchAll();
    } catch (e) {
      console.error(e);
    }
  };

  const getProjectName = (id) => projects.find(p => p.project_id === id)?.project_name || id;
  const getEmployeeName = (id) => {
    const e = employees.find(e => e.employee_id === id);
    return e ? `${e.first_name} ${e.last_name}` : id || "—";
  };

  const totalOpen     = issues.filter(i => i.status === "Open").length;
  const totalCritical = issues.filter(i => i.severity === "Critical").length;
  const totalSafety   = issues.filter(i => i.category === "Safety").length;
  const totalResolved = issues.filter(i => i.status === "Resolved" || i.status === "Closed").length;

  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "60vh" }}>
      <div style={{ textAlign: "center" }}>
        <div style={{ width: 40, height: 40, border: "3px solid #e5e7eb", borderTopColor: "#6366f1", borderRadius: "50%", animation: "spin 0.8s linear infinite", margin: "0 auto 12px" }} />
        <p style={{ color: "#6b7280", fontSize: 14 }}>Chargement des incidents...</p>
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );

  return (
    <div style={{ padding: "24px 32px", background: "#f8fafc", minHeight: "100vh" }}>

      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 700, color: "#111827", margin: 0 }}>Gestion des Incidents</h1>
          <p style={{ color: "#6b7280", fontSize: 14, margin: "4px 0 0" }}>Suivi et résolution des problèmes sur chantiers</p>
        </div>
        {canEdit && (
          <button onClick={openCreate} style={{ display: "flex", alignItems: "center", gap: 8, background: "#6366f1", color: "#fff", border: "none", borderRadius: 10, padding: "10px 20px", fontSize: 14, fontWeight: 600, cursor: "pointer" }}>
            ＋ Nouvel Incident
          </button>
        )}
      </div>

      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 24 }}>
        {[
          { label: "Incidents Ouverts",  value: totalOpen,     color: "#ef4444", bg: "#fef2f2", icon: "🔴" },
          { label: "Incidents Critiques",value: totalCritical, color: "#f97316", bg: "#fff7ed", icon: "⚠️" },
          { label: "Incidents Sécurité", value: totalSafety,   color: "#8b5cf6", bg: "#f5f3ff", icon: "🦺" },
          { label: "Résolus / Clôturés", value: totalResolved, color: "#22c55e", bg: "#f0fdf4", icon: "✅" },
        ].map(s => (
          <div key={s.label} style={{ background: "#fff", borderRadius: 12, padding: "16px 20px", boxShadow: "0 1px 3px rgba(0,0,0,0.06)", border: "1px solid #f1f5f9" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <p style={{ fontSize: 12, color: "#6b7280", margin: "0 0 8px", fontWeight: 500 }}>{s.label}</p>
                <p style={{ fontSize: 28, fontWeight: 700, color: s.color, margin: 0 }}>{s.value}</p>
              </div>
              <div style={{ width: 40, height: 40, background: s.bg, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>{s.icon}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
        <div style={{ flex: 1, minWidth: 260, position: "relative" }}>
          <span style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#9ca3af", fontSize: 16 }}>🔍</span>
          <input
            value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Rechercher un incident..."
            style={{ width: "100%", padding: "10px 12px 10px 36px", border: "1px solid #e5e7eb", borderRadius: 10, fontSize: 14, outline: "none", boxSizing: "border-box", background: "#fff" }}
          />
        </div>
        {[
          { value: filterSeverity, set: setFilterSeverity, options: ["Critical","High","Medium","Low"], placeholder: "Toutes les sévérités" },
          { value: filterCategory, set: setFilterCategory, options: ["Safety","Quality","Delay","Budget","Technical","Other"], placeholder: "Toutes les catégories" },
        ].map((f, i) => (
          <select key={i} value={f.value} onChange={e => f.set(e.target.value)}
            style={{ padding: "10px 16px", border: "1px solid #e5e7eb", borderRadius: 10, fontSize: 14, background: "#fff", cursor: "pointer", outline: "none" }}>
            <option value="">{f.placeholder}</option>
            {f.options.map(o => <option key={o} value={o}>{o}</option>)}
          </select>
        ))}
        <select value={filterProject} onChange={e => setFilterProject(e.target.value)}
          style={{ padding: "10px 16px", border: "1px solid #e5e7eb", borderRadius: 10, fontSize: 14, background: "#fff", cursor: "pointer", outline: "none", maxWidth: 220 }}>
          <option value="">Tous les projets</option>
          {projects.map(p => <option key={p.project_id} value={p.project_id}>{p.project_name}</option>)}
        </select>
      </div>

      {/* Kanban Board */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, alignItems: "start" }}>
        {STATUS_COLUMNS.map(col => {
          const colIssues = byStatus(col.key);
          return (
            <div key={col.key}>
              {/* Column Header */}
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12, padding: "8px 12px", background: "#fff", borderRadius: 10, border: "1px solid #f1f5f9" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 14 }}>{col.icon}</span>
                  <span style={{ fontWeight: 600, color: "#374151", fontSize: 14 }}>{col.label}</span>
                </div>
                <span style={{ background: col.color, color: "#fff", borderRadius: 20, padding: "2px 10px", fontSize: 12, fontWeight: 700 }}>{colIssues.length}</span>
              </div>

              {/* Cards */}
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {colIssues.length === 0 && (
                  <div style={{ textAlign: "center", padding: "32px 16px", color: "#d1d5db", fontSize: 13, background: "#fff", borderRadius: 12, border: "1px dashed #e5e7eb" }}>
                    Aucun incident
                  </div>
                )}
                {colIssues.map(issue => {
                  const sev = SEVERITY_CONFIG[issue.severity] || SEVERITY_CONFIG.Medium;
                  const cat = CATEGORY_CONFIG[issue.category]  || CATEGORY_CONFIG.Other;
                  return (
                    <div key={issue.issue_id} style={{ background: "#fff", borderRadius: 12, border: `1px solid #e5e7eb`, borderLeft: `4px solid ${sev.color}`, padding: "14px 16px", boxShadow: "0 1px 3px rgba(0,0,0,0.05)", transition: "box-shadow 0.2s" }}
                      onMouseEnter={e => e.currentTarget.style.boxShadow = "0 4px 12px rgba(0,0,0,0.1)"}
                      onMouseLeave={e => e.currentTarget.style.boxShadow = "0 1px 3px rgba(0,0,0,0.05)"}
                    >
                      {/* Card Header */}
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                        <span style={{ fontSize: 11, color: "#9ca3af", fontWeight: 600 }}>{issue.issue_id}</span>
                        {canEdit && (
                          <div style={{ display: "flex", gap: 6 }}>
                            <button onClick={() => openEdit(issue)} style={{ background: "none", border: "none", cursor: "pointer", color: "#9ca3af", padding: 2, fontSize: 14 }}>✏️</button>
                            <button onClick={() => handleDelete(issue.issue_id)} style={{ background: "none", border: "none", cursor: "pointer", color: "#9ca3af", padding: 2, fontSize: 14 }}>🗑️</button>
                          </div>
                        )}
                      </div>

                      {/* Title */}
                      <h3 style={{ fontSize: 14, fontWeight: 600, color: "#111827", margin: "0 0 6px", lineHeight: 1.4 }}>{issue.title}</h3>

                      {/* Description */}
                      <p style={{ fontSize: 12, color: "#6b7280", margin: "0 0 10px", lineHeight: 1.5, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
                        {issue.description}
                      </p>

                      {/* Badges */}
                      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10 }}>
                        <span style={{ fontSize: 11, fontWeight: 600, color: sev.color, background: sev.bg, border: `1px solid ${sev.border}`, borderRadius: 6, padding: "2px 8px" }}>
                          {issue.severity}
                        </span>
                        <span style={{ fontSize: 11, fontWeight: 600, color: cat.color, background: cat.bg, borderRadius: 6, padding: "2px 8px" }}>
                          {cat.icon} {issue.category}
                        </span>
                        <span style={{ fontSize: 11, fontWeight: 600, color: "#6366f1", background: "#f0f0ff", borderRadius: 6, padding: "2px 8px" }}>
                          {issue.project_id}
                        </span>
                      </div>

                      {/* Meta */}
                      <div style={{ fontSize: 11, color: "#9ca3af", display: "flex", flexDirection: "column", gap: 3, marginBottom: 10 }}>
                        <div>👤 Rapporté par: <strong style={{ color: "#374151" }}>{getEmployeeName(issue.reported_by)}</strong></div>
                        {issue.assigned_to && <div>🔧 Assigné à: <strong style={{ color: "#374151" }}>{getEmployeeName(issue.assigned_to)}</strong></div>}
                        <div>📅 {formatDate(issue.created_date)}{issue.resolved_date ? ` → ${formatDate(issue.resolved_date)}` : ""}</div>
                        <div>🏗️ {getProjectName(issue.project_id)}</div>
                      </div>

                      {/* Resolution notes */}
                      {issue.resolution_notes && (
                        <div style={{ background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 8, padding: "6px 10px", fontSize: 11, color: "#166534", marginBottom: 10 }}>
                          ✅ {issue.resolution_notes}
                        </div>
                      )}

                      {/* Status change buttons */}
                      {canEdit && (
                        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                          {STATUS_COLUMNS.filter(s => s.key !== col.key).map(s => (
                            <button key={s.key} onClick={() => handleStatusChange(issue, s.key)}
                              style={{ fontSize: 10, padding: "3px 8px", border: `1px solid ${s.color}`, borderRadius: 6, background: "#fff", color: s.color, cursor: "pointer", fontWeight: 600 }}>
                              → {s.label}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Modal */}
      {showModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: 20 }}>
          <div style={{ background: "#fff", borderRadius: 16, padding: 28, width: "100%", maxWidth: 540, maxHeight: "90vh", overflowY: "auto", boxShadow: "0 20px 60px rgba(0,0,0,0.2)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
              <h2 style={{ fontSize: 18, fontWeight: 700, color: "#111827", margin: 0 }}>
                {editIssue ? "Modifier l'incident" : "Nouvel Incident"}
              </h2>
              <button onClick={() => setShowModal(false)} style={{ background: "none", border: "none", fontSize: 20, cursor: "pointer", color: "#6b7280" }}>✕</button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {[
                { label: "Titre *", key: "title", type: "text" },
                { label: "Description", key: "description", type: "textarea" },
              ].map(f => (
                <div key={f.key}>
                  <label style={{ fontSize: 13, fontWeight: 600, color: "#374151", display: "block", marginBottom: 6 }}>{f.label}</label>
                  {f.type === "textarea" ? (
                    <textarea value={form[f.key]} onChange={e => setForm({...form, [f.key]: e.target.value})}
                      rows={3} style={{ width: "100%", padding: "9px 12px", border: "1px solid #e5e7eb", borderRadius: 8, fontSize: 14, outline: "none", resize: "vertical", boxSizing: "border-box" }} />
                  ) : (
                    <input value={form[f.key]} onChange={e => setForm({...form, [f.key]: e.target.value})}
                      style={{ width: "100%", padding: "9px 12px", border: "1px solid #e5e7eb", borderRadius: 8, fontSize: 14, outline: "none", boxSizing: "border-box" }} />
                  )}
                </div>
              ))}

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div>
                  <label style={{ fontSize: 13, fontWeight: 600, color: "#374151", display: "block", marginBottom: 6 }}>Projet *</label>
                  <select value={form.project_id} onChange={e => setForm({...form, project_id: e.target.value})}
                    style={{ width: "100%", padding: "9px 12px", border: "1px solid #e5e7eb", borderRadius: 8, fontSize: 14, outline: "none" }}>
                    <option value="">Sélectionner...</option>
                    {projects.map(p => <option key={p.project_id} value={p.project_id}>{p.project_name}</option>)}
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 13, fontWeight: 600, color: "#374151", display: "block", marginBottom: 6 }}>Assigné à</label>
                  <select value={form.assigned_to} onChange={e => setForm({...form, assigned_to: e.target.value})}
                    style={{ width: "100%", padding: "9px 12px", border: "1px solid #e5e7eb", borderRadius: 8, fontSize: 14, outline: "none" }}>
                    <option value="">Non assigné</option>
                    {employees.map(e => <option key={e.employee_id} value={e.employee_id}>{e.first_name} {e.last_name}</option>)}
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 13, fontWeight: 600, color: "#374151", display: "block", marginBottom: 6 }}>Sévérité</label>
                  <select value={form.severity} onChange={e => setForm({...form, severity: e.target.value})}
                    style={{ width: "100%", padding: "9px 12px", border: "1px solid #e5e7eb", borderRadius: 8, fontSize: 14, outline: "none" }}>
                    {["Critical","High","Medium","Low"].map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 13, fontWeight: 600, color: "#374151", display: "block", marginBottom: 6 }}>Catégorie</label>
                  <select value={form.category} onChange={e => setForm({...form, category: e.target.value})}
                    style={{ width: "100%", padding: "9px 12px", border: "1px solid #e5e7eb", borderRadius: 8, fontSize: 14, outline: "none" }}>
                    {["Safety","Quality","Delay","Budget","Technical","Other"].map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 13, fontWeight: 600, color: "#374151", display: "block", marginBottom: 6 }}>Statut</label>
                  <select value={form.status} onChange={e => setForm({...form, status: e.target.value})}
                    style={{ width: "100%", padding: "9px 12px", border: "1px solid #e5e7eb", borderRadius: 8, fontSize: 14, outline: "none" }}>
                    {["Open","In Progress","Resolved","Closed"].map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
              </div>

              {(form.status === "Resolved" || form.status === "Closed") && (
                <div>
                  <label style={{ fontSize: 13, fontWeight: 600, color: "#374151", display: "block", marginBottom: 6 }}>Notes de résolution</label>
                  <textarea value={form.resolution_notes || ""} onChange={e => setForm({...form, resolution_notes: e.target.value})}
                    rows={2} placeholder="Décrivez comment l'incident a été résolu..."
                    style={{ width: "100%", padding: "9px 12px", border: "1px solid #e5e7eb", borderRadius: 8, fontSize: 14, outline: "none", resize: "vertical", boxSizing: "border-box" }} />
                </div>
              )}

              <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 8 }}>
                <button onClick={() => setShowModal(false)}
                  style={{ padding: "10px 20px", border: "1px solid #e5e7eb", borderRadius: 8, background: "#fff", color: "#374151", cursor: "pointer", fontSize: 14, fontWeight: 600 }}>
                  Annuler
                </button>
                <button onClick={handleSave}
                  style={{ padding: "10px 20px", border: "none", borderRadius: 8, background: "#6366f1", color: "#fff", cursor: "pointer", fontSize: 14, fontWeight: 600 }}>
                  {editIssue ? "Enregistrer" : "Créer"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}