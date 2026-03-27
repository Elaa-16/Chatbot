import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { getProjects, createProject, updateProject, deleteProject, getEmployees } from '../services/api';
import {
  Plus, Pencil, Trash2, X, MapPin, DollarSign,
  Calendar, TrendingUp, Building2, Search, ChevronDown,
  CheckCircle2, Clock, Circle, PauseCircle, Save
} from 'lucide-react';

// ── Status config ─────────────────────────────────────────────────────────────
const STATUS = {
  'Planning':    { bg:'#faf5ff', color:'#7c3aed', border:'#ddd6fe', icon:<Circle size={12}/>,       label:'Planifié' },
  'In Progress': { bg:'#eff6ff', color:'#2563eb', border:'#bfdbfe', icon:<Clock size={12}/>,         label:'En cours' },
  'Completed':   { bg:'#f0fdf4', color:'#16a34a', border:'#bbf7d0', icon:<CheckCircle2 size={12}/>,  label:'Terminé' },
  'On Hold':     { bg:'#fffbeb', color:'#d97706', border:'#fde68a', icon:<PauseCircle size={12}/>,   label:'En pause' },
};

const StatusBadge = ({ status }) => {
  const s = STATUS[status] || STATUS['Planning'];
  return (
    <span style={{ display:'inline-flex', alignItems:'center', gap:5, background:s.bg, color:s.color, border:`1px solid ${s.border}`, borderRadius:20, padding:'3px 10px', fontSize:11, fontWeight:700, whiteSpace:'nowrap' }}>
      {s.icon}{s.label}
    </span>
  );
};

// ── Progress bar ──────────────────────────────────────────────────────────────
const ProgressBar = ({ pct }) => {
  const n = parseFloat(pct) || 0;
  const color = n >= 80 ? '#16a34a' : n >= 50 ? '#6366f1' : n >= 30 ? '#f59e0b' : '#ef4444';
  return (
    <div style={{ display:'flex', alignItems:'center', gap:8 }}>
      <div style={{ flex:1, height:5, background:'#f1f5f9', borderRadius:99, overflow:'hidden' }}>
        <div style={{ width:`${Math.min(n,100)}%`, height:'100%', background:color, borderRadius:99, transition:'width 0.6s ease' }} />
      </div>
      <span style={{ fontSize:11, fontWeight:700, color, minWidth:30, textAlign:'right' }}>{n}%</span>
    </div>
  );
};

// ── Modal field ───────────────────────────────────────────────────────────────
const Field = ({ label, children, col = 1 }) => (
  <div style={{ gridColumn: `span ${col}` }}>
    <label style={{ display:'block', fontSize:11, fontWeight:700, color:'#64748b', textTransform:'uppercase', letterSpacing:'0.07em', marginBottom:5 }}>{label}</label>
    {children}
  </div>
);

const inputStyle = {
  width:'100%', padding:'9px 12px', border:'1px solid #e2e8f0', borderRadius:8,
  fontSize:14, background:'#f8fafc', boxSizing:'border-box', outline:'none',
  fontFamily:'inherit', color:'#1e293b',
};

const selectStyle = { ...inputStyle, appearance:'none', cursor:'pointer' };

// ── Main ──────────────────────────────────────────────────────────────────────
const Projects = () => {
  const { isCEO, isManager } = useAuth();
  const canEdit = isCEO || isManager;

  const [projects,  setProjects]  = useState([]);
  const [employees, setEmployees] = useState([]);
  const [loading,   setLoading]   = useState(true);
  const [search,    setSearch]    = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [modal,     setModal]     = useState(null); // null | { mode, project? }
  const [formData,  setFormData]  = useState({});
  const [selectedEmps, setSelectedEmps] = useState([]);
  const [saving,    setSaving]    = useState(false);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [pR, eR] = await Promise.all([getProjects(), getEmployees()]);
      setProjects(pR.data);
      setEmployees(eR.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const openCreate = () => {
    setFormData({
      project_id:'', project_name:'', project_type:'', client_name:'',
      start_date:'', end_date:'', status:'Planning', budget:'',
      actual_cost:0, completion_percentage:0, location:'',
      project_manager_id:'', site_supervisor_id:'', description:'',
    });
    setSelectedEmps([]);
    setModal({ mode:'create' });
  };

  const openEdit = (project) => {
    setFormData(project);
    setSelectedEmps(project.assigned_employees ? project.assigned_employees.split(';').filter(Boolean) : []);
    setModal({ mode:'edit', project });
  };

  const openDelete = (project) => setModal({ mode:'delete', project });

  const handleSubmit = async () => {
    setSaving(true);
    try {
      const auto = [formData.project_manager_id, formData.site_supervisor_id].filter(Boolean);
      const all  = [...new Set([...selectedEmps, ...auto])];
      const data = { ...formData, assigned_employees: all.join(';') };
      if (modal.mode === 'edit') {
        await updateProject(modal.project.project_id, data);
      } else {
        await createProject(data);
      }
      setModal(null);
      loadData();
    } catch (e) {
      alert(e.response?.data?.detail || 'Erreur lors de la sauvegarde');
    } finally { setSaving(false); }
  };

  const handleDelete = async () => {
    setSaving(true);
    try {
      await deleteProject(modal.project.project_id);
      setModal(null);
      loadData();
    } catch (e) {
      alert(e.response?.data?.detail || 'Erreur lors de la suppression');
    } finally { setSaving(false); }
  };

  const toggle = id => setSelectedEmps(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);

  const set = (k, v) => setFormData(f => ({ ...f, [k]: v }));

  const filtered = projects.filter(p => {
    const q = search.toLowerCase();
    const matchSearch = !q || `${p.project_name} ${p.client_name} ${p.location}`.toLowerCase().includes(q);
    const matchStatus = !filterStatus || p.status === filterStatus;
    return matchSearch && matchStatus;
  });

  if (loading) return (
    <div style={{ display:'flex', alignItems:'center', justifyContent:'center', height:300, gap:12 }}>
      <div style={{ width:36, height:36, border:'3px solid #e2e8f0', borderTop:'3px solid #6366f1', borderRadius:'50%', animation:'spin 0.8s linear infinite' }} />
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:20, fontFamily:"'Segoe UI',system-ui,sans-serif" }}>
      <style>{`
        @keyframes spin{to{transform:rotate(360deg)}}
        @keyframes fadeUp{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
        .proj-card{transition:box-shadow .18s,transform .18s;}
        .proj-card:hover{box-shadow:0 8px 28px rgba(99,102,241,.13)!important;transform:translateY(-2px);}
        .action-btn{transition:all .15s;}
        .action-btn:hover{opacity:.85;transform:scale(1.04);}
        .emp-row{transition:background .12s;cursor:pointer;}
        .emp-row:hover{background:#f0f4ff!important;}
      `}</style>

      {/* ── Header ── */}
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', flexWrap:'wrap', gap:12, animation:'fadeUp .4s both' }}>
        <div>
          <h1 style={{ fontSize:26, fontWeight:800, color:'#0f172a', margin:0, letterSpacing:'-0.02em' }}>Projets</h1>
          <p style={{ color:'#64748b', fontSize:14, margin:'4px 0 0' }}>{filtered.length} projet{filtered.length>1?'s':''} {search||filterStatus?'filtrés':'au total'}</p>
        </div>
        <div style={{ display:'flex', gap:10, alignItems:'center', flexWrap:'wrap' }}>
          {/* Search */}
          <div style={{ position:'relative' }}>
            <Search size={14} style={{ position:'absolute', left:10, top:'50%', transform:'translateY(-50%)', color:'#94a3b8' }} />
            <input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Rechercher..."
              style={{ ...inputStyle, paddingLeft:32, width:200 }} />
          </div>
          {/* Status filter */}
          <div style={{ position:'relative' }}>
            <select value={filterStatus} onChange={e=>setFilterStatus(e.target.value)}
              style={{ ...selectStyle, width:160, paddingRight:30 }}>
              <option value="">Tous les statuts</option>
              {Object.entries(STATUS).map(([k,v]) => <option key={k} value={k}>{v.label}</option>)}
            </select>
            <ChevronDown size={13} style={{ position:'absolute', right:10, top:'50%', transform:'translateY(-50%)', color:'#94a3b8', pointerEvents:'none' }} />
          </div>
          {canEdit && (
            <button onClick={openCreate} style={{ display:'flex', alignItems:'center', gap:7, padding:'9px 18px', background:'linear-gradient(135deg,#4f46e5,#6366f1)', color:'#fff', border:'none', borderRadius:9, fontWeight:700, fontSize:14, cursor:'pointer', boxShadow:'0 4px 14px rgba(99,102,241,.35)', whiteSpace:'nowrap' }}>
              <Plus size={16} /> Nouveau projet
            </button>
          )}
        </div>
      </div>

      {/* ── Grid ── */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(320px,1fr))', gap:16 }}>
        {filtered.map((project, idx) => {
          const s = STATUS[project.status] || STATUS['Planning'];
          const pct = project.completion_percentage || 0;
          const budgetM = project.budget ? `${(project.budget/1_000_000).toFixed(1)}M TND` : '—';

          return (
            <div key={project.project_id} className="proj-card" style={{ background:'#fff', borderRadius:14, border:`1px solid ${s.border}`, padding:0, boxShadow:'0 1px 3px rgba(0,0,0,.06)', overflow:'hidden', animation:`fadeUp .4s ${idx*0.04}s both` }}>
              {/* Color top strip */}
              <div style={{ height:4, background:`linear-gradient(90deg,${s.color},${s.color}88)` }} />

              <div style={{ padding:'18px 20px' }}>
                {/* Header */}
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:12, gap:8 }}>
                  <div style={{ flex:1, minWidth:0 }}>
                    <div style={{ fontWeight:800, fontSize:15, color:'#0f172a', lineHeight:1.3, marginBottom:3 }}>{project.project_name}</div>
                    <div style={{ fontSize:11, color:'#94a3b8', fontWeight:600 }}>{project.project_id}</div>
                  </div>
                  <StatusBadge status={project.status} />
                </div>

                {/* Info rows */}
                <div style={{ display:'flex', flexDirection:'column', gap:6, marginBottom:14 }}>
                  {[
                    { icon:<Building2 size={12} color="#94a3b8"/>, value: project.client_name },
                    { icon:<MapPin size={12} color="#94a3b8"/>,    value: project.location },
                    { icon:<DollarSign size={12} color="#94a3b8"/>, value: budgetM },
                    { icon:<Calendar size={12} color="#94a3b8"/>,  value: project.end_date ? `Fin : ${project.end_date}` : null },
                  ].filter(r => r.value).map((r, i) => (
                    <div key={i} style={{ display:'flex', alignItems:'center', gap:6, fontSize:13, color:'#64748b' }}>
                      {r.icon}<span style={{ overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{r.value}</span>
                    </div>
                  ))}
                </div>

                {/* Progress */}
                <div style={{ marginBottom: canEdit ? 14 : 0 }}>
                  <div style={{ display:'flex', justifyContent:'space-between', marginBottom:5 }}>
                    <span style={{ fontSize:11, fontWeight:700, color:'#64748b', textTransform:'uppercase', letterSpacing:'0.06em' }}>Avancement</span>
                    <TrendingUp size={12} color="#94a3b8" />
                  </div>
                  <ProgressBar pct={pct} />
                </div>

                {/* Actions — CEO and Manager only */}
                {canEdit && (
                  <div style={{ display:'flex', gap:8, paddingTop:14, borderTop:'1px solid #f8fafc' }}>
                    <button className="action-btn" onClick={() => openEdit(project)} style={{ flex:1, display:'flex', alignItems:'center', justifyContent:'center', gap:6, padding:'8px', background:'#eef2ff', color:'#4f46e5', border:'none', borderRadius:8, fontWeight:600, fontSize:13, cursor:'pointer' }}>
                      <Pencil size={13} /> Modifier
                    </button>
                    <button className="action-btn" onClick={() => openDelete(project)} style={{ flex:1, display:'flex', alignItems:'center', justifyContent:'center', gap:6, padding:'8px', background:'#fef2f2', color:'#ef4444', border:'none', borderRadius:8, fontWeight:600, fontSize:13, cursor:'pointer' }}>
                      <Trash2 size={13} /> Supprimer
                    </button>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Create / Edit Modal ── */}
      {(modal?.mode === 'create' || modal?.mode === 'edit') && (
        <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.55)', zIndex:1000, display:'flex', alignItems:'center', justifyContent:'center', padding:20, backdropFilter:'blur(4px)' }}>
          <div style={{ background:'#fff', borderRadius:18, width:'100%', maxWidth:700, maxHeight:'92vh', overflow:'hidden', display:'flex', flexDirection:'column', boxShadow:'0 32px 80px rgba(0,0,0,.25)' }}>

            {/* Modal header */}
            <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'20px 28px', borderBottom:'1px solid #f1f5f9', flexShrink:0 }}>
              <div>
                <h2 style={{ fontSize:18, fontWeight:800, color:'#0f172a', margin:0 }}>
                  {modal.mode === 'edit' ? `✏️ Modifier — ${modal.project.project_name}` : '➕ Nouveau projet'}
                </h2>
                <p style={{ fontSize:13, color:'#64748b', margin:'3px 0 0' }}>
                  {modal.mode === 'edit' ? 'Modifier les informations du projet' : 'Créer un nouveau projet de construction'}
                </p>
              </div>
              <button onClick={() => setModal(null)} style={{ width:34, height:34, borderRadius:9, border:'1px solid #e2e8f0', background:'#f8fafc', cursor:'pointer', display:'flex', alignItems:'center', justifyContent:'center' }}>
                <X size={16} color="#64748b" />
              </button>
            </div>

            {/* Modal body */}
            <div style={{ overflowY:'auto', flex:1, padding:'24px 28px' }}>

              {/* Section 1 — Infos */}
              <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:16 }}>
                <div style={{ width:26, height:26, borderRadius:7, background:'#eef2ff', display:'flex', alignItems:'center', justifyContent:'center', fontSize:12, fontWeight:800, color:'#4f46e5' }}>1</div>
                <span style={{ fontWeight:700, fontSize:15, color:'#0f172a' }}>Informations du projet</span>
              </div>

              <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:14, marginBottom:24 }}>
                <Field label="ID Projet *">
                  <input value={formData.project_id||''} onChange={e=>set('project_id',e.target.value)}
                    style={inputStyle} disabled={modal.mode==='edit'} required />
                </Field>
                <Field label="Nom du projet *">
                  <input value={formData.project_name||''} onChange={e=>set('project_name',e.target.value)} style={inputStyle} required />
                </Field>
                <Field label="Type">
                  <div style={{ position:'relative' }}>
                    <select value={formData.project_type||''} onChange={e=>set('project_type',e.target.value)} style={{ ...selectStyle, paddingRight:30 }}>
                      <option value="">Sélectionner...</option>
                      {['Residential','Commercial','Industrial','Infrastructure','Healthcare','Education'].map(t=>(
                        <option key={t} value={t}>{t}</option>
                      ))}
                    </select>
                    <ChevronDown size={13} style={{ position:'absolute', right:10, top:'50%', transform:'translateY(-50%)', color:'#94a3b8', pointerEvents:'none' }} />
                  </div>
                </Field>
                <Field label="Client">
                  <input value={formData.client_name||''} onChange={e=>set('client_name',e.target.value)} style={inputStyle} />
                </Field>
                <Field label="Date de début">
                  <input type="date" value={formData.start_date||''} onChange={e=>set('start_date',e.target.value)} style={inputStyle} />
                </Field>
                <Field label="Date de fin">
                  <input type="date" value={formData.end_date||''} onChange={e=>set('end_date',e.target.value)} style={inputStyle} />
                </Field>
                <Field label="Statut">
                  <div style={{ position:'relative' }}>
                    <select value={formData.status||'Planning'} onChange={e=>set('status',e.target.value)} style={{ ...selectStyle, paddingRight:30 }}>
                      {Object.entries(STATUS).map(([k,v])=><option key={k} value={k}>{v.label}</option>)}
                    </select>
                    <ChevronDown size={13} style={{ position:'absolute', right:10, top:'50%', transform:'translateY(-50%)', color:'#94a3b8', pointerEvents:'none' }} />
                  </div>
                </Field>
                <Field label="Lieu">
                  <input value={formData.location||''} onChange={e=>set('location',e.target.value)} style={inputStyle} />
                </Field>
                <Field label="Budget (TND)">
                  <input type="number" value={formData.budget||''} onChange={e=>set('budget',parseFloat(e.target.value))} style={inputStyle} />
                </Field>
                <Field label="Coût actuel (TND)">
                  <input type="number" value={formData.actual_cost||0} onChange={e=>set('actual_cost',parseFloat(e.target.value))} style={inputStyle} />
                </Field>
                <Field label="Avancement (%)">
                  <input type="number" min="0" max="100" value={formData.completion_percentage||0} onChange={e=>set('completion_percentage',parseInt(e.target.value))} style={inputStyle} />
                </Field>
                <Field label="Chef de projet">
                  <div style={{ position:'relative' }}>
                    <select value={formData.project_manager_id||''} onChange={e=>set('project_manager_id',e.target.value)} style={{ ...selectStyle, paddingRight:30 }}>
                      <option value="">Sélectionner...</option>
                      {employees.filter(e=>e.role==='manager'||e.role==='ceo').map(e=>(
                        <option key={e.employee_id} value={e.employee_id}>{e.first_name} {e.last_name}</option>
                      ))}
                    </select>
                    <ChevronDown size={13} style={{ position:'absolute', right:10, top:'50%', transform:'translateY(-50%)', color:'#94a3b8', pointerEvents:'none' }} />
                  </div>
                </Field>
                <Field label="Chef de chantier">
                  <div style={{ position:'relative' }}>
                    <select value={formData.site_supervisor_id||''} onChange={e=>set('site_supervisor_id',e.target.value)} style={{ ...selectStyle, paddingRight:30 }}>
                      <option value="">Sélectionner...</option>
                      {employees.filter(e=>e.role==='employee'||e.role==='manager').map(e=>(
                        <option key={e.employee_id} value={e.employee_id}>{e.first_name} {e.last_name}</option>
                      ))}
                    </select>
                    <ChevronDown size={13} style={{ position:'absolute', right:10, top:'50%', transform:'translateY(-50%)', color:'#94a3b8', pointerEvents:'none' }} />
                  </div>
                </Field>
                <Field label="Description" col={2}>
                  <textarea value={formData.description||''} onChange={e=>set('description',e.target.value)}
                    rows={3} style={{ ...inputStyle, resize:'vertical' }} />
                </Field>
              </div>

              {/* Section 2 — Employees */}
              <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:14 }}>
                <div style={{ width:26, height:26, borderRadius:7, background:'#eef2ff', display:'flex', alignItems:'center', justifyContent:'center', fontSize:12, fontWeight:800, color:'#4f46e5' }}>2</div>
                <span style={{ fontWeight:700, fontSize:15, color:'#0f172a' }}>Assigner des employés</span>
                {selectedEmps.length > 0 && (
                  <span style={{ background:'#eef2ff', color:'#4f46e5', borderRadius:20, padding:'2px 10px', fontSize:12, fontWeight:700 }}>
                    {selectedEmps.length} sélectionné{selectedEmps.length>1?'s':''}
                  </span>
                )}
              </div>
              <p style={{ fontSize:13, color:'#94a3b8', marginBottom:12 }}>
                Le chef de projet et chef de chantier sont inclus automatiquement.
              </p>

              <div style={{ border:'1px solid #e2e8f0', borderRadius:10, maxHeight:220, overflowY:'auto' }}>
                {employees.filter(e=>e.role==='employee'||e.role==='manager').map((emp, i) => {
                  const checked = selectedEmps.includes(emp.employee_id);
                  return (
                    <div key={emp.employee_id} className="emp-row" onClick={() => toggle(emp.employee_id)}
                      style={{ display:'flex', alignItems:'center', gap:12, padding:'10px 14px', background: checked ? '#eef2ff' : i%2===0?'#fff':'#fafafa', borderBottom: i < employees.length-1 ? '1px solid #f1f5f9' : 'none' }}>
                      <div style={{ width:18, height:18, borderRadius:5, border:`2px solid ${checked?'#6366f1':'#cbd5e1'}`, background:checked?'#6366f1':'#fff', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0, transition:'all .15s' }}>
                        {checked && <svg width="10" height="8" viewBox="0 0 10 8"><polyline points="1,4 4,7 9,1" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>}
                      </div>
                      <div style={{ width:32, height:32, borderRadius:'50%', background:checked?'#c7d2fe':'#e2e8f0', display:'flex', alignItems:'center', justifyContent:'center', fontSize:12, fontWeight:700, color:checked?'#4f46e5':'#64748b', flexShrink:0 }}>
                        {emp.first_name[0]}{emp.last_name[0]}
                      </div>
                      <div style={{ flex:1, minWidth:0 }}>
                        <div style={{ fontWeight:600, fontSize:13, color:'#0f172a' }}>{emp.first_name} {emp.last_name}</div>
                        <div style={{ fontSize:11, color:'#94a3b8' }}>{emp.position}</div>
                      </div>
                      <span style={{ fontSize:11, fontWeight:700, background:emp.role==='manager'?'#dbeafe':'#dcfce7', color:emp.role==='manager'?'#1d4ed8':'#15803d', borderRadius:20, padding:'2px 9px', flexShrink:0 }}>
                        {emp.role==='manager'?'Manager':'Employé'}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Modal footer */}
            <div style={{ padding:'16px 28px', borderTop:'1px solid #f1f5f9', display:'flex', gap:10, flexShrink:0 }}>
              <button onClick={() => setModal(null)} style={{ padding:'10px 22px', borderRadius:9, border:'1px solid #e2e8f0', background:'#fff', color:'#64748b', fontWeight:600, fontSize:14, cursor:'pointer' }}>
                Annuler
              </button>
              <button onClick={handleSubmit} disabled={saving} style={{ flex:1, padding:'10px', borderRadius:9, border:'none', background:'linear-gradient(135deg,#4f46e5,#6366f1)', color:'#fff', fontWeight:700, fontSize:14, cursor:saving?'not-allowed':'pointer', display:'flex', alignItems:'center', justifyContent:'center', gap:7, opacity:saving?.7:1 }}>
                <Save size={15} />
                {saving ? 'Sauvegarde...' : modal.mode==='edit' ? 'Mettre à jour' : 'Créer le projet'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Delete confirm ── */}
      {modal?.mode === 'delete' && (
        <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.55)', zIndex:1000, display:'flex', alignItems:'center', justifyContent:'center', padding:20, backdropFilter:'blur(4px)' }}>
          <div style={{ background:'#fff', borderRadius:18, padding:36, maxWidth:420, width:'100%', boxShadow:'0 32px 80px rgba(0,0,0,.25)', textAlign:'center' }}>
            <div style={{ width:60, height:60, borderRadius:'50%', background:'#fef2f2', display:'flex', alignItems:'center', justifyContent:'center', margin:'0 auto 18px' }}>
              <Trash2 size={26} color="#ef4444" />
            </div>
            <h3 style={{ fontSize:19, fontWeight:800, color:'#0f172a', margin:'0 0 10px' }}>Supprimer ce projet ?</h3>
            <p style={{ fontSize:14, color:'#64748b', margin:'0 0 8px' }}>
              <strong style={{ color:'#0f172a' }}>{modal.project.project_name}</strong>
            </p>
            <p style={{ fontSize:13, color:'#94a3b8', margin:'0 0 28px' }}>Cette action est irréversible. Toutes les données associées seront perdues.</p>
            <div style={{ display:'flex', gap:10 }}>
              <button onClick={()=>setModal(null)} style={{ flex:1, padding:'11px', borderRadius:9, border:'1px solid #e2e8f0', background:'#fff', color:'#64748b', fontWeight:600, cursor:'pointer', fontSize:14 }}>
                Annuler
              </button>
              <button onClick={handleDelete} disabled={saving} style={{ flex:1, padding:'11px', borderRadius:9, border:'none', background:'#ef4444', color:'#fff', fontWeight:700, cursor:saving?'not-allowed':'pointer', fontSize:14, opacity:saving?.7:1 }}>
                {saving?'Suppression...':'Supprimer'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Projects;