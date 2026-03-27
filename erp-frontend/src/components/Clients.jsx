import React, { useState, useEffect } from 'react';
import { Building2, Eye, X, FolderKanban, MapPin, Search, ChevronRight } from 'lucide-react';
import { getProjects } from '../services/api';

// ── Client type ───────────────────────────────────────────────────────────────
const getClientType = (name) => {
  if (!name) return { label:'Autre', bg:'#f8fafc', color:'#64748b' };
  if (name.includes('Ministère') || name.includes('Municipalité') || name.includes('Gouvernorat'))
    return { label:'Gouvernement', bg:'#faf5ff', color:'#7c3aed' };
  if (name.includes('ONAS') || name.includes('UNESCO') || name.includes('Association'))
    return { label:'Public', bg:'#eff6ff', color:'#2563eb' };
  if (name.includes('Société') || name.includes(' SA') || name.includes('Group') || name.includes('Tunisia'))
    return { label:'Entreprise', bg:'#f0fdf4', color:'#16a34a' };
  return { label:'Particulier', bg:'#fffbeb', color:'#d97706' };
};

// ── Status pill ───────────────────────────────────────────────────────────────
const STATUS = {
  'In Progress': { bg:'#eff6ff', color:'#2563eb', label:'En cours' },
  'Completed':   { bg:'#f0fdf4', color:'#16a34a', label:'Terminé' },
  'Planning':    { bg:'#faf5ff', color:'#7c3aed', label:'Planifié' },
  'On Hold':     { bg:'#fffbeb', color:'#d97706', label:'En pause' },
};

const StatusPill = ({ status }) => {
  const s = STATUS[status] || { bg:'#f8fafc', color:'#64748b', label: status };
  return <span style={{ background:s.bg, color:s.color, borderRadius:20, padding:'3px 10px', fontSize:11, fontWeight:700 }}>{s.label}</span>;
};

// ── Progress bar ──────────────────────────────────────────────────────────────
const Bar = ({ pct, color = '#6366f1' }) => (
  <div style={{ height:5, background:'#f1f5f9', borderRadius:99, overflow:'hidden' }}>
    <div style={{ width:`${Math.min(pct,100)}%`, height:'100%', background:color, borderRadius:99, transition:'width .6s ease' }} />
  </div>
);

// ── Main ──────────────────────────────────────────────────────────────────────
const Clients = () => {
  const [clients,  setClients]  = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [search,   setSearch]   = useState('');
  const [selected, setSelected] = useState(null);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const res  = await getProjects();
      const data = res.data;
      setProjects(data);

      const map = {};
      data.forEach(p => {
        if (!p.client_name) return;
        if (!map[p.client_name]) map[p.client_name] = {
          client_name: p.client_name, total_projects:0,
          total_budget:0, total_actual_cost:0,
          active_projects:0, completed_projects:0,
        };
        const c = map[p.client_name];
        c.total_projects++;
        c.total_budget      += p.budget      || 0;
        c.total_actual_cost += p.actual_cost || 0;
        if (['In Progress','Planning'].includes(p.status)) c.active_projects++;
        if (p.status === 'Completed')                      c.completed_projects++;
      });
      setClients(Object.values(map).sort((a,b) => b.total_budget - a.total_budget));
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const filtered = clients.filter(c =>
    !search || c.client_name.toLowerCase().includes(search.toLowerCase())
  );

  const totalBudget     = clients.reduce((s,c) => s + c.total_budget, 0);
  const totalActive     = clients.reduce((s,c) => s + c.active_projects, 0);
  const totalCompleted  = clients.reduce((s,c) => s + c.completed_projects, 0);

  const clientProjects = selected ? projects.filter(p => p.client_name === selected.client_name) : [];

  if (loading) return (
    <div style={{ display:'flex', alignItems:'center', justifyContent:'center', height:300, gap:12 }}>
      <div style={{ width:36, height:36, border:'3px solid #e2e8f0', borderTop:'3px solid #6366f1', borderRadius:'50%', animation:'spin .8s linear infinite' }} />
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:20, fontFamily:"'Segoe UI',system-ui,sans-serif" }}>
      <style>{`
        @keyframes spin{to{transform:rotate(360deg)}}
        @keyframes fadeUp{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
        .client-card{transition:box-shadow .18s,transform .18s;}
        .client-card:hover{box-shadow:0 8px 28px rgba(99,102,241,.13)!important;transform:translateY(-2px);}
        .view-btn{transition:all .15s;}
        .view-btn:hover{background:#eef2ff!important;color:#4f46e5!important;}
        .proj-row{transition:background .12s;}
        .proj-row:hover{background:#f8fafc!important;}
      `}</style>

      {/* ── Header ── */}
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', flexWrap:'wrap', gap:12, animation:'fadeUp .4s both' }}>
        <div>
          <h1 style={{ fontSize:26, fontWeight:800, color:'#0f172a', margin:0, letterSpacing:'-0.02em' }}>Clients</h1>
          <p style={{ color:'#64748b', fontSize:14, margin:'4px 0 0' }}>
            {filtered.length} client{filtered.length>1?'s':''}{search?' trouvés':' au total'}
          </p>
        </div>
        <div style={{ position:'relative' }}>
          <Search size={14} style={{ position:'absolute', left:10, top:'50%', transform:'translateY(-50%)', color:'#94a3b8' }} />
          <input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Rechercher un client..."
            style={{ padding:'9px 12px 9px 32px', border:'1px solid #e2e8f0', borderRadius:8, fontSize:14, background:'#f8fafc', width:220, outline:'none' }} />
        </div>
      </div>

      {/* ── Summary stats ── */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(160px,1fr))', gap:12, animation:'fadeUp .4s .05s both' }}>
        {[
          { label:'Clients',          value: clients.length,                             color:'#6366f1', bg:'#eef2ff', border:'#c7d2fe' },
          { label:'Projets actifs',   value: totalActive,                                color:'#16a34a', bg:'#f0fdf4', border:'#bbf7d0' },
          { label:'Projets terminés', value: totalCompleted,                             color:'#2563eb', bg:'#eff6ff', border:'#bfdbfe' },
          { label:'Budget total',     value: `${(totalBudget/1_000_000).toFixed(1)}M TND`, color:'#7c3aed', bg:'#faf5ff', border:'#ddd6fe' },
        ].map((s,i) => (
          <div key={i} style={{ background:s.bg, border:`1px solid ${s.border}`, borderRadius:12, padding:'14px 16px' }}>
            <div style={{ fontSize:22, fontWeight:800, color:s.color, lineHeight:1 }}>{s.value}</div>
            <div style={{ fontSize:11, fontWeight:600, color:'#64748b', marginTop:4 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* ── Client grid ── */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(300px,1fr))', gap:16 }}>
        {filtered.map((client, i) => {
          const ct       = getClientType(client.client_name);
          const budgetPct = client.total_budget > 0
            ? ((client.total_actual_cost / client.total_budget) * 100)
            : 0;
          const overBudget = budgetPct > 100;
          const initials  = client.client_name.split(' ').map(w=>w[0]).slice(0,2).join('').toUpperCase();

          return (
            <div key={i} className="client-card" style={{ background:'#fff', borderRadius:14, border:'1px solid #f1f5f9', overflow:'hidden', boxShadow:'0 1px 3px rgba(0,0,0,.05)', animation:`fadeUp .4s ${i*.04}s both` }}>
              {/* Top strip */}
              <div style={{ height:4, background:`linear-gradient(90deg,${ct.color},${ct.color}55)` }} />

              <div style={{ padding:'18px 20px' }}>
                {/* Header */}
                <div style={{ display:'flex', alignItems:'flex-start', gap:12, marginBottom:14 }}>
                  <div style={{ width:44, height:44, borderRadius:12, background:ct.bg, border:`1.5px solid ${ct.color}33`, display:'flex', alignItems:'center', justifyContent:'center', fontSize:14, fontWeight:800, color:ct.color, flexShrink:0 }}>
                    {initials}
                  </div>
                  <div style={{ flex:1, minWidth:0 }}>
                    <div style={{ fontWeight:800, fontSize:14, color:'#0f172a', lineHeight:1.3, marginBottom:4 }}>{client.client_name}</div>
                    <span style={{ background:ct.bg, color:ct.color, borderRadius:20, padding:'2px 9px', fontSize:11, fontWeight:700 }}>{ct.label}</span>
                  </div>
                </div>

                {/* Project counts */}
                <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:8, marginBottom:14 }}>
                  {[
                    { label:'Total',     value: client.total_projects,    color:'#0f172a' },
                    { label:'En cours',  value: client.active_projects,   color:'#16a34a' },
                    { label:'Terminés',  value: client.completed_projects, color:'#2563eb' },
                  ].map((m,j) => (
                    <div key={j} style={{ background:'#f8fafc', borderRadius:9, padding:'9px 10px', textAlign:'center' }}>
                      <div style={{ fontSize:18, fontWeight:800, color:m.color }}>{m.value}</div>
                      <div style={{ fontSize:10, color:'#94a3b8', fontWeight:600, marginTop:2 }}>{m.label}</div>
                    </div>
                  ))}
                </div>

                {/* Financial */}
                <div style={{ background:'#f8fafc', borderRadius:10, padding:'12px 14px', marginBottom:14 }}>
                  <div style={{ display:'flex', justifyContent:'space-between', marginBottom:8 }}>
                    <div>
                      <div style={{ fontSize:10, fontWeight:700, color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.06em' }}>Budget</div>
                      <div style={{ fontSize:15, fontWeight:800, color:'#6366f1' }}>{(client.total_budget/1_000_000).toFixed(2)}M TND</div>
                    </div>
                    <div style={{ textAlign:'right' }}>
                      <div style={{ fontSize:10, fontWeight:700, color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.06em' }}>Dépensé</div>
                      <div style={{ fontSize:15, fontWeight:800, color: overBudget ? '#ef4444' : '#f59e0b' }}>
                        {(client.total_actual_cost/1_000_000).toFixed(2)}M TND
                      </div>
                    </div>
                  </div>
                  <Bar pct={budgetPct} color={overBudget ? '#ef4444' : '#6366f1'} />
                  <div style={{ textAlign:'right', fontSize:11, fontWeight:700, color: overBudget?'#ef4444':'#6366f1', marginTop:4 }}>
                    {budgetPct.toFixed(1)}% utilisé
                  </div>
                </div>

                {/* View button */}
                <button className="view-btn" onClick={() => setSelected(client)}
                  style={{ width:'100%', display:'flex', alignItems:'center', justifyContent:'center', gap:7, padding:'9px', background:'#f8fafc', border:'1px solid #e2e8f0', borderRadius:9, color:'#64748b', fontWeight:600, fontSize:13, cursor:'pointer' }}>
                  <Eye size={14} /> Voir les projets
                  <ChevronRight size={13} style={{ marginLeft:'auto' }} />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {filtered.length === 0 && (
        <div style={{ textAlign:'center', padding:'48px 0', background:'#fff', borderRadius:14, border:'1px solid #f1f5f9' }}>
          <Building2 size={48} color="#e2e8f0" style={{ margin:'0 auto 12px', display:'block' }} />
          <p style={{ color:'#94a3b8', fontSize:15, fontWeight:600 }}>Aucun client trouvé</p>
        </div>
      )}

      {/* ── Details Modal ── */}
      {selected && (
        <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.55)', zIndex:1000, display:'flex', alignItems:'center', justifyContent:'center', padding:20, backdropFilter:'blur(4px)' }}>
          <div style={{ background:'#fff', borderRadius:18, width:'100%', maxWidth:720, maxHeight:'90vh', overflow:'hidden', display:'flex', flexDirection:'column', boxShadow:'0 32px 80px rgba(0,0,0,.25)' }}>

            {/* Modal header */}
            <div style={{ padding:'22px 28px', borderBottom:'1px solid #f1f5f9', flexShrink:0 }}>
              <div style={{ display:'flex', alignItems:'flex-start', justifyContent:'space-between', gap:12 }}>
                <div>
                  <h2 style={{ fontSize:20, fontWeight:800, color:'#0f172a', margin:0 }}>{selected.client_name}</h2>
                  <div style={{ display:'flex', gap:12, marginTop:8, flexWrap:'wrap' }}>
                    {[
                      { label:`${selected.total_projects} projets`, color:'#64748b' },
                      { label:`${selected.active_projects} en cours`, color:'#16a34a' },
                      { label:`${selected.completed_projects} terminés`, color:'#2563eb' },
                    ].map((m,i) => (
                      <span key={i} style={{ fontSize:12, fontWeight:700, color:m.color }}>{m.label}</span>
                    ))}
                  </div>
                </div>
                <button onClick={() => setSelected(null)} style={{ width:34, height:34, borderRadius:9, border:'1px solid #e2e8f0', background:'#f8fafc', cursor:'pointer', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
                  <X size={16} color="#64748b" />
                </button>
              </div>
            </div>

            {/* Financial summary */}
            <div style={{ margin:'0 28px', marginTop:20, background:'linear-gradient(135deg,#eef2ff,#faf5ff)', borderRadius:14, padding:'18px 20px', flexShrink:0 }}>
              <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:16 }}>
                {[
                  { label:'Budget total', value:`${(selected.total_budget/1_000_000).toFixed(2)}M TND`, color:'#4f46e5' },
                  { label:'Dépensé',      value:`${(selected.total_actual_cost/1_000_000).toFixed(2)}M TND`, color:'#f59e0b' },
                  { label:'Restant',      value:`${((selected.total_budget-selected.total_actual_cost)/1_000_000).toFixed(2)}M TND`, color:'#16a34a' },
                ].map((m,i) => (
                  <div key={i}>
                    <div style={{ fontSize:11, fontWeight:700, color:'#64748b', textTransform:'uppercase', letterSpacing:'0.06em' }}>{m.label}</div>
                    <div style={{ fontSize:22, fontWeight:800, color:m.color, marginTop:4 }}>{m.value}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Projects list */}
            <div style={{ flex:1, overflowY:'auto', padding:'20px 28px' }}>
              <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:14 }}>
                <FolderKanban size={16} color="#6366f1" />
                <span style={{ fontWeight:700, fontSize:15, color:'#0f172a' }}>Projets ({clientProjects.length})</span>
              </div>
              <div style={{ display:'flex', flexDirection:'column', gap:10 }}>
                {clientProjects.map((p, i) => {
                  const pct = p.completion_percentage || 0;
                  const col = pct>=70 ? '#16a34a' : pct>=40 ? '#f59e0b' : '#ef4444';
                  return (
                    <div key={p.project_id} className="proj-row" style={{ background:'#fff', border:'1px solid #f1f5f9', borderRadius:12, padding:'14px 16px', transition:'background .12s' }}>
                      <div style={{ display:'flex', alignItems:'flex-start', justifyContent:'space-between', marginBottom:10 }}>
                        <div>
                          <div style={{ fontWeight:700, fontSize:14, color:'#0f172a' }}>{p.project_name}</div>
                          <div style={{ display:'flex', alignItems:'center', gap:6, marginTop:3, fontSize:12, color:'#94a3b8' }}>
                            {p.project_type && <span>{p.project_type}</span>}
                            {p.project_type && p.location && <span>•</span>}
                            {p.location && <><MapPin size={11} /><span>{p.location}</span></>}
                          </div>
                        </div>
                        <StatusPill status={p.status} />
                      </div>
                      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:12, marginBottom:10 }}>
                        {[
                          { label:'Budget',   value:`${(p.budget||0).toLocaleString()} TND`,      color:'#6366f1' },
                          { label:'Dépensé',  value:`${(p.actual_cost||0).toLocaleString()} TND`, color:'#f59e0b' },
                          { label:'Avancement', value:`${pct}%`,                                     color:col },
                        ].map((m,j) => (
                          <div key={j}>
                            <div style={{ fontSize:10, fontWeight:700, color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.06em' }}>{m.label}</div>
                            <div style={{ fontSize:14, fontWeight:800, color:m.color, marginTop:2 }}>{m.value}</div>
                          </div>
                        ))}
                      </div>
                      <Bar pct={pct} color={col} />
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Clients;