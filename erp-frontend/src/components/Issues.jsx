import { useState, useEffect, useCallback } from "react";
import api from "../services/api";
import { Plus, Pencil, Trash2, X, Save, ChevronDown, Search } from "lucide-react";

const SEV = {
  Critical: { color:"#ef4444", bg:"#fef2f2", border:"#fecaca" },
  High:     { color:"#f97316", bg:"#fff7ed", border:"#fed7aa" },
  Medium:   { color:"#eab308", bg:"#fefce8", border:"#fef08a" },
  Low:      { color:"#22c55e", bg:"#f0fdf4", border:"#bbf7d0" },
};

const CAT = {
  Safety:    { icon:"🦺", color:"#ef4444", bg:"#fef2f2" },
  Quality:   { icon:"✅", color:"#8b5cf6", bg:"#f5f3ff" },
  Delay:     { icon:"⏱️", color:"#f97316", bg:"#fff7ed" },
  Budget:    { icon:"💰", color:"#10b981", bg:"#f0fdf4" },
  Technical: { icon:"⚙️", color:"#3b82f6", bg:"#eff6ff" },
  Other:     { icon:"📋", color:"#6b7280", bg:"#f9fafb" },
};

const COLS = [
  { key:"Open",        label:"Ouvert",   color:"#ef4444", bg:"#fef2f2" },
  { key:"In Progress", label:"En cours", color:"#f97316", bg:"#fff7ed" },
  { key:"Resolved",    label:"Résolu",   color:"#22c55e", bg:"#f0fdf4" },
  { key:"Closed",      label:"Clôturé",  color:"#6b7280", bg:"#f8fafc" },
];

const fmt = d => d ? new Date(d).toLocaleDateString("fr-FR", { day:"2-digit", month:"short" }) : "—";

const inputSt = { width:"100%", padding:"9px 12px", border:"1px solid #e2e8f0", borderRadius:8, fontSize:14, outline:"none", boxSizing:"border-box", background:"#f8fafc", fontFamily:"inherit" };

export default function Issues() {
  const [issues,    setIssues]    = useState([]);
  const [projects,  setProjects]  = useState([]);
  const [employees, setEmployees] = useState([]);
  const [loading,   setLoading]   = useState(true);
  const [search,    setSearch]    = useState("");
  const [fSev,      setFSev]      = useState("");
  const [fCat,      setFCat]      = useState("");
  const [modal,     setModal]     = useState(null);
  const [saving,    setSaving]    = useState(false);
  const [form,      setForm]      = useState({});

  const userRole = localStorage.getItem("user_role");
  const canEdit  = userRole === "ceo" || userRole === "manager";

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [iR, pR, eR] = await Promise.all([api.get("/issues"), api.get("/projects"), api.get("/employees")]);
      setIssues(iR.data); setProjects(pR.data); setEmployees(eR.data);
    } catch(e) { console.error(e); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = issues.filter(i => {
    const q = search.toLowerCase();
    return (!q || i.title?.toLowerCase().includes(q) || i.description?.toLowerCase().includes(q))
      && (!fSev || i.severity === fSev)
      && (!fCat || i.category === fCat);
  });

  const byCol = k => filtered.filter(i => i.status === k);

  const openCreate = () => {
    setForm({ issue_id:`IS${Date.now()}`, project_id:"", title:"", description:"", severity:"Medium", category:"Safety", status:"Open", assigned_to:"" });
    setModal("create");
  };

  const openEdit = issue => { setForm({...issue}); setModal("edit"); };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (modal === "edit") await api.put(`/issues/${form.issue_id}`, form);
      else await api.post("/issues", { ...form, reported_by: localStorage.getItem("user_id") });
      setModal(null); load();
    } catch(e) { console.error(e); }
    finally { setSaving(false); }
  };

  const handleDelete = async id => {
    if (!window.confirm("Supprimer cet incident ?")) return;
    try { await api.delete(`/issues/${id}`); load(); } catch(e) { console.error(e); }
  };

  const moveStatus = async (issue, status) => {
    try { await api.put(`/issues/${issue.issue_id}`, { status }); load(); } catch(e) { console.error(e); }
  };

  const projName = id => projects.find(p => p.project_id === id)?.project_name || id;
  const empName  = id => { const e = employees.find(e => e.employee_id === id); return e ? `${e.first_name} ${e.last_name}` : id || "—"; };

  const totOpen     = issues.filter(i => i.status === "Open").length;
  const totCritical = issues.filter(i => i.severity === "Critical").length;
  const totSafety   = issues.filter(i => i.category === "Safety").length;
  const totResolved = issues.filter(i => ["Resolved","Closed"].includes(i.status)).length;

  const F = ({label, children}) => (
    <div>
      <label style={{ display:"block", fontSize:11, fontWeight:700, color:"#64748b", textTransform:"uppercase", letterSpacing:"0.07em", marginBottom:5 }}>{label}</label>
      {children}
    </div>
  );

  if (loading) return (
    <div style={{ display:"flex", alignItems:"center", justifyContent:"center", height:300, gap:12 }}>
      <div style={{ width:36, height:36, border:"3px solid #e2e8f0", borderTop:"3px solid #6366f1", borderRadius:"50%", animation:"spin .8s linear infinite" }} />
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:20, fontFamily:"'Segoe UI',system-ui,sans-serif" }}>
      <style>{`
        @keyframes spin{to{transform:rotate(360deg)}}
        @keyframes fadeUp{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
        .iss-card{transition:box-shadow .18s,transform .18s;}
        .iss-card:hover{box-shadow:0 6px 20px rgba(0,0,0,.1)!important;transform:translateY(-1px);}
        .move-btn{transition:all .15s;border:none;cursor:pointer;font-size:10px;fontWeight:700;border-radius:6px;padding:3px 8px;}
        .move-btn:hover{opacity:.8;}
        .act-btn{transition:all .15s;background:none;border:none;cursor:pointer;border-radius:6px;padding:4px;display:flex;align-items:center;}
        .act-btn:hover{background:#f1f5f9;}
      `}</style>

      {/* Header */}
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", flexWrap:"wrap", gap:12, animation:"fadeUp .4s both" }}>
        <div>
          <h1 style={{ fontSize:26, fontWeight:800, color:"#0f172a", margin:0, letterSpacing:"-0.02em" }}>Incidents</h1>
          <p style={{ color:"#64748b", fontSize:14, margin:"4px 0 0" }}>Suivi et résolution des problèmes sur chantiers</p>
        </div>
        {canEdit && (
          <button onClick={openCreate} style={{ display:"flex", alignItems:"center", gap:7, padding:"9px 18px", background:"linear-gradient(135deg,#4f46e5,#6366f1)", color:"#fff", border:"none", borderRadius:9, fontWeight:700, fontSize:14, cursor:"pointer", boxShadow:"0 4px 14px rgba(99,102,241,.35)" }}>
            <Plus size={16} /> Nouvel incident
          </button>
        )}
      </div>

      {/* Stats */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(150px,1fr))", gap:12, animation:"fadeUp .4s .05s both" }}>
        {[
          { label:"Ouverts",         value:totOpen,     color:"#ef4444", bg:"#fef2f2", border:"#fecaca" },
          { label:"Critiques",       value:totCritical, color:"#f97316", bg:"#fff7ed", border:"#fed7aa" },
          { label:"Sécurité",        value:totSafety,   color:"#8b5cf6", bg:"#f5f3ff", border:"#ddd6fe" },
          { label:"Résolus/Clôturés",value:totResolved, color:"#22c55e", bg:"#f0fdf4", border:"#bbf7d0" },
        ].map((s,i) => (
          <div key={i} style={{ background:s.bg, border:`1px solid ${s.border}`, borderRadius:12, padding:"14px 16px" }}>
            <div style={{ fontSize:26, fontWeight:800, color:s.color, lineHeight:1 }}>{s.value}</div>
            <div style={{ fontSize:11, fontWeight:600, color:"#64748b", marginTop:4 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div style={{ display:"flex", gap:10, flexWrap:"wrap", animation:"fadeUp .4s .1s both" }}>
        <div style={{ position:"relative", flex:1, minWidth:220 }}>
          <Search size={14} style={{ position:"absolute", left:10, top:"50%", transform:"translateY(-50%)", color:"#94a3b8" }} />
          <input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Rechercher..."
            style={{ ...inputSt, paddingLeft:32, background:"#fff" }} />
        </div>
        {[
          { val:fSev, set:setFSev, opts:["Critical","High","Medium","Low"], ph:"Sévérité" },
          { val:fCat, set:setFCat, opts:["Safety","Quality","Delay","Budget","Technical","Other"], ph:"Catégorie" },
        ].map((f,i) => (
          <div key={i} style={{ position:"relative" }}>
            <select value={f.val} onChange={e=>f.set(e.target.value)} style={{ ...inputSt, paddingRight:28, appearance:"none", cursor:"pointer", background:"#fff", width:"auto", minWidth:140 }}>
              <option value="">{f.ph}</option>
              {f.opts.map(o=><option key={o} value={o}>{o}</option>)}
            </select>
            <ChevronDown size={13} style={{ position:"absolute", right:8, top:"50%", transform:"translateY(-50%)", color:"#94a3b8", pointerEvents:"none" }} />
          </div>
        ))}
      </div>

      {/* Kanban */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:14, alignItems:"start", animation:"fadeUp .4s .15s both" }}>
        {COLS.map(col => {
          const items = byCol(col.key);
          return (
            <div key={col.key}>
              {/* Column header */}
              <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:10, padding:"9px 14px", background:"#fff", borderRadius:10, border:"1px solid #f1f5f9", boxShadow:"0 1px 3px rgba(0,0,0,.04)" }}>
                <div style={{ display:"flex", alignItems:"center", gap:8 }}>
                  <div style={{ width:8, height:8, borderRadius:"50%", background:col.color }} />
                  <span style={{ fontWeight:700, color:"#0f172a", fontSize:13 }}>{col.label}</span>
                </div>
                <span style={{ background:col.bg, color:col.color, border:`1px solid ${col.color}33`, borderRadius:20, padding:"1px 9px", fontSize:11, fontWeight:800 }}>{items.length}</span>
              </div>

              {/* Cards */}
              <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
                {items.length === 0 && (
                  <div style={{ textAlign:"center", padding:"28px 12px", color:"#cbd5e1", fontSize:12, background:"#fff", borderRadius:10, border:"1px dashed #e2e8f0" }}>
                    Aucun incident
                  </div>
                )}
                {items.map(issue => {
                  const sev = SEV[issue.severity] || SEV.Medium;
                  const cat = CAT[issue.category]  || CAT.Other;
                  return (
                    <div key={issue.issue_id} className="iss-card" style={{ background:"#fff", borderRadius:12, border:`1px solid #e2e8f0`, borderLeft:`4px solid ${sev.color}`, padding:"13px 14px", boxShadow:"0 1px 3px rgba(0,0,0,.05)" }}>
                      {/* Top row */}
                      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:7 }}>
                        <span style={{ fontSize:10, color:"#94a3b8", fontWeight:700 }}>{issue.issue_id}</span>
                        {canEdit && (
                          <div style={{ display:"flex", gap:2 }}>
                            <button className="act-btn" onClick={()=>openEdit(issue)} title="Modifier"><Pencil size={12} color="#64748b" /></button>
                            <button className="act-btn" onClick={()=>handleDelete(issue.issue_id)} title="Supprimer"><Trash2 size={12} color="#ef4444" /></button>
                          </div>
                        )}
                      </div>

                      {/* Title */}
                      <div style={{ fontWeight:700, fontSize:13, color:"#0f172a", lineHeight:1.4, marginBottom:6 }}>{issue.title}</div>

                      {/* Description */}
                      {issue.description && (
                        <div style={{ fontSize:11, color:"#94a3b8", marginBottom:9, lineHeight:1.5, display:"-webkit-box", WebkitLineClamp:2, WebkitBoxOrient:"vertical", overflow:"hidden" }}>
                          {issue.description}
                        </div>
                      )}

                      {/* Badges */}
                      <div style={{ display:"flex", gap:5, flexWrap:"wrap", marginBottom:9 }}>
                        <span style={{ fontSize:10, fontWeight:700, color:sev.color, background:sev.bg, border:`1px solid ${sev.border}`, borderRadius:6, padding:"2px 7px" }}>{issue.severity}</span>
                        <span style={{ fontSize:10, fontWeight:700, color:cat.color, background:cat.bg, borderRadius:6, padding:"2px 7px" }}>{cat.icon} {issue.category}</span>
                        <span style={{ fontSize:10, fontWeight:700, color:"#6366f1", background:"#eef2ff", borderRadius:6, padding:"2px 7px" }}>{issue.project_id}</span>
                      </div>

                      {/* Meta */}
                      <div style={{ fontSize:11, color:"#94a3b8", display:"flex", flexDirection:"column", gap:3, marginBottom:9, borderTop:"1px solid #f8fafc", paddingTop:7 }}>
                        {issue.assigned_to && <div>🔧 <strong style={{ color:"#475569" }}>{empName(issue.assigned_to)}</strong></div>}
                        <div>📅 {fmt(issue.created_date)} · 🏗️ {projName(issue.project_id)}</div>
                      </div>

                      {/* Resolution note */}
                      {issue.resolution_notes && (
                        <div style={{ background:"#f0fdf4", border:"1px solid #bbf7d0", borderRadius:8, padding:"6px 9px", fontSize:11, color:"#166534", marginBottom:8 }}>
                          ✅ {issue.resolution_notes}
                        </div>
                      )}

                      {/* Move buttons */}
                      {canEdit && (
                        <div style={{ display:"flex", gap:5, flexWrap:"wrap" }}>
                          {COLS.filter(c=>c.key!==col.key).map(c=>(
                            <button key={c.key} className="move-btn" onClick={()=>moveStatus(issue,c.key)}
                              style={{ background:c.bg, color:c.color, border:`1px solid ${c.color}44` }}>
                              → {c.label}
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
      {(modal === "create" || modal === "edit") && (
        <div style={{ position:"fixed", inset:0, background:"rgba(0,0,0,0.5)", zIndex:1000, display:"flex", alignItems:"center", justifyContent:"center", padding:20, backdropFilter:"blur(4px)" }}>
          <div style={{ background:"#fff", borderRadius:18, width:"100%", maxWidth:540, maxHeight:"92vh", overflow:"hidden", display:"flex", flexDirection:"column", boxShadow:"0 32px 80px rgba(0,0,0,.22)" }}>
            <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", padding:"18px 24px", borderBottom:"1px solid #f1f5f9" }}>
              <h2 style={{ fontSize:17, fontWeight:800, color:"#0f172a", margin:0 }}>
                {modal==="edit" ? "✏️ Modifier l'incident" : "⚠️ Nouvel incident"}
              </h2>
              <button onClick={()=>setModal(null)} style={{ width:32, height:32, borderRadius:8, border:"1px solid #e2e8f0", background:"#f8fafc", cursor:"pointer", display:"flex", alignItems:"center", justifyContent:"center" }}>
                <X size={15} color="#64748b" />
              </button>
            </div>

            <div style={{ padding:"20px 24px", overflowY:"auto", flex:1, display:"flex", flexDirection:"column", gap:13 }}>
              <F label="Titre *"><input value={form.title||""} onChange={e=>setForm(f=>({...f,title:e.target.value}))} style={inputSt} /></F>
              <F label="Description"><textarea value={form.description||""} onChange={e=>setForm(f=>({...f,description:e.target.value}))} rows={3} style={{ ...inputSt, resize:"vertical" }} /></F>

              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
                <F label="Projet *">
                  <select value={form.project_id||""} onChange={e=>setForm(f=>({...f,project_id:e.target.value}))} style={{ ...inputSt, appearance:"none", cursor:"pointer" }}>
                    <option value="">Sélectionner...</option>
                    {projects.map(p=><option key={p.project_id} value={p.project_id}>{p.project_name}</option>)}
                  </select>
                </F>
                <F label="Assigné à">
                  <select value={form.assigned_to||""} onChange={e=>setForm(f=>({...f,assigned_to:e.target.value}))} style={{ ...inputSt, appearance:"none", cursor:"pointer" }}>
                    <option value="">Non assigné</option>
                    {employees.map(e=><option key={e.employee_id} value={e.employee_id}>{e.first_name} {e.last_name}</option>)}
                  </select>
                </F>
                <F label="Sévérité">
                  <select value={form.severity||"Medium"} onChange={e=>setForm(f=>({...f,severity:e.target.value}))} style={{ ...inputSt, appearance:"none", cursor:"pointer" }}>
                    {["Critical","High","Medium","Low"].map(s=><option key={s} value={s}>{s}</option>)}
                  </select>
                </F>
                <F label="Catégorie">
                  <select value={form.category||"Safety"} onChange={e=>setForm(f=>({...f,category:e.target.value}))} style={{ ...inputSt, appearance:"none", cursor:"pointer" }}>
                    {["Safety","Quality","Delay","Budget","Technical","Other"].map(c=><option key={c} value={c}>{c}</option>)}
                  </select>
                </F>
                <F label="Statut">
                  <select value={form.status||"Open"} onChange={e=>setForm(f=>({...f,status:e.target.value}))} style={{ ...inputSt, appearance:"none", cursor:"pointer" }}>
                    {["Open","In Progress","Resolved","Closed"].map(s=><option key={s} value={s}>{s}</option>)}
                  </select>
                </F>
              </div>

              {["Resolved","Closed"].includes(form.status) && (
                <F label="Notes de résolution">
                  <textarea value={form.resolution_notes||""} onChange={e=>setForm(f=>({...f,resolution_notes:e.target.value}))}
                    rows={2} placeholder="Comment l'incident a été résolu..." style={{ ...inputSt, resize:"vertical" }} />
                </F>
              )}
            </div>

            <div style={{ padding:"16px 24px", borderTop:"1px solid #f1f5f9", display:"flex", gap:10 }}>
              <button onClick={()=>setModal(null)} style={{ padding:"10px 20px", borderRadius:8, border:"1px solid #e2e8f0", background:"#fff", color:"#64748b", fontWeight:600, fontSize:14, cursor:"pointer" }}>
                Annuler
              </button>
              <button onClick={handleSave} disabled={saving} style={{ flex:1, padding:"10px", borderRadius:8, border:"none", background:"linear-gradient(135deg,#4f46e5,#6366f1)", color:"#fff", fontWeight:700, fontSize:14, cursor:saving?"not-allowed":"pointer", display:"flex", alignItems:"center", justifyContent:"center", gap:6, opacity:saving?.7:1 }}>
                <Save size={14} />{saving?"Sauvegarde...":modal==="edit"?"Enregistrer":"Créer l'incident"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}