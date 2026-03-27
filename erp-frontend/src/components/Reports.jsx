import React, { useState, useEffect } from 'react';
import {
  FileBarChart, Download, Calendar,
  TrendingUp, Users, DollarSign, CheckSquare,
  Plus, RefreshCw, Lock, X
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

const REPORT_TYPES = [
  { value:'project_status',       label:'Rapport Projet',    icon:TrendingUp,   color:'#3b82f6', bg:'#eff6ff' },
  { value:'employee_performance', label:'Rapport Employé',   icon:Users,        color:'#8b5cf6', bg:'#f5f3ff' },
  { value:'budget',               label:'Rapport Financier', icon:DollarSign,   color:'#10b981', bg:'#f0fdf4' },
  { value:'task_completion',      label:'Rapport KPI',       icon:CheckSquare,  color:'#f59e0b', bg:'#fffbeb' },
  { value:'custom',               label:'Personnalisé',      icon:FileBarChart, color:'#6366f1', bg:'#eef2ff', ceoOnly:true },
];

const STATUS_STYLE = {
  Completed: { bg:'#f0fdf4', color:'#16a34a', border:'#bbf7d0' },
  Pending:   { bg:'#fffbeb', color:'#d97706', border:'#fde68a' },
  Failed:    { bg:'#fef2f2', color:'#dc2626', border:'#fecaca' },
};

const fmt = d => d ? new Date(d).toLocaleDateString('fr-FR', { day:'numeric', month:'long', year:'numeric' }) : '—';

const Reports = () => {
  const { user, isCEO, isManager } = useAuth();
  const [reports,    setReports]    = useState([]);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState(null);
  const [modal,      setModal]      = useState(false);
  const [generating, setGenerating] = useState(false);

  const yr = new Date().getFullYear();
  const [form, setForm] = useState({
    report_type:'project_status', title:'',
    period_start:`${yr}-01-01`, period_end:`${yr}-12-31`,
  });

  const reportTypes = REPORT_TYPES.filter(t => !t.ceoOnly || isCEO);
 // eslint-disable-next-line react-hooks/exhaustive-deps
useEffect(() => {
  if (!isCEO && !isManager) { setLoading(false); return; }
  load();
}, [user, isCEO, isManager]); // ← ajoutez les deux ici

  const load = async () => {
    try {
      setLoading(true);
      const res = await api.get('/reports');
      setReports(res.data); setError(null);
    } catch(e) { setError(e.response?.data?.detail || 'Erreur chargement'); }
    finally { setLoading(false); }
  };

  const generate = async e => {
    e.preventDefault();
    setGenerating(true);
    try {
      await api.post('/reports/generate', {
        report_id:    `REP${Date.now()}`,
        report_type:  form.report_type,
        title:        form.title || `${REPORT_TYPES.find(t=>t.value===form.report_type)?.label} — ${new Date().toLocaleDateString('fr-FR')}`,
        period_start: form.period_start,
        period_end:   form.period_end,
        generated_by: user?.employee_id || 'E001',
        filters:      '{}', parameters: '{}',
      });
      setModal(false); load();
    } catch(e) { setError(e.response?.data?.detail || 'Erreur génération'); }
    finally { setGenerating(false); }
  };

  // ── Dans Reports.jsx, remplacez la fonction download() par celle-ci ──────────

const download = async (report) => {
  try {
    const token = localStorage.getItem('token');
    const response = await fetch(
      `http://localhost:8000/reports/${report.report_id}/download`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    if (!response.ok) throw new Error('Erreur serveur');
    const blob = await response.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `${report.title || report.report_id}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    alert('Erreur lors du telechargement : ' + e.message);
  }
};

  const getType = v => REPORT_TYPES.find(t=>t.value===v) || REPORT_TYPES[0];

  if (!loading && !isCEO && !isManager) return (
    <div style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', height:300, gap:12 }}>
      <div style={{ width:64, height:64, borderRadius:'50%', background:'#f1f5f9', display:'flex', alignItems:'center', justifyContent:'center' }}>
        <Lock size={28} color="#94a3b8" />
      </div>
      <p style={{ color:'#64748b', fontSize:15, fontWeight:600 }}>Accès réservé aux managers et CEO</p>
    </div>
  );

  if (loading) return (
    <div style={{ display:'flex', alignItems:'center', justifyContent:'center', height:300, gap:12 }}>
      <div style={{ width:36, height:36, border:'3px solid #e2e8f0', borderTop:'3px solid #6366f1', borderRadius:'50%', animation:'spin .8s linear infinite' }} />
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );

  const thisMonth = reports.filter(r => {
    const d = new Date(r.generation_date); const n = new Date();
    return d.getMonth()===n.getMonth() && d.getFullYear()===n.getFullYear();
  }).length;

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:20, fontFamily:"'Segoe UI',system-ui,sans-serif" }}>
      <style>{`
        @keyframes spin{to{transform:rotate(360deg)}}
        @keyframes fadeUp{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
        .rep-card{transition:box-shadow .18s,transform .18s;}
        .rep-card:hover{box-shadow:0 8px 24px rgba(99,102,241,.12)!important;transform:translateY(-2px);}
        .rt-opt{transition:all .15s;cursor:pointer;border-radius:10px;padding:12px 14px;border:2px solid #e2e8f0;background:#fff;display:flex;align-items:center;gap:10px;}
        .rt-opt:hover{border-color:#a5b4fc;}
        .rt-opt.sel{border-color:#6366f1;background:#eef2ff;}
      `}</style>

      {/* Header */}
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', flexWrap:'wrap', gap:12, animation:'fadeUp .4s both' }}>
        <div>
          <h1 style={{ fontSize:26, fontWeight:800, color:'#0f172a', margin:0, letterSpacing:'-0.02em' }}>Rapports</h1>
          <p style={{ color:'#64748b', fontSize:14, margin:'4px 0 0' }}>
            {isCEO ? "Tous les rapports de l'entreprise" : "Vos rapports générés"}
          </p>
        </div>
        <div style={{ display:'flex', gap:10 }}>
          <button onClick={load} style={{ display:'flex', alignItems:'center', gap:6, padding:'9px 16px', background:'#fff', border:'1px solid #e2e8f0', borderRadius:9, fontWeight:600, fontSize:13, color:'#64748b', cursor:'pointer' }}>
            <RefreshCw size={14} /> Actualiser
          </button>
          <button onClick={()=>setModal(true)} style={{ display:'flex', alignItems:'center', gap:7, padding:'9px 18px', background:'linear-gradient(135deg,#4f46e5,#6366f1)', color:'#fff', border:'none', borderRadius:9, fontWeight:700, fontSize:14, cursor:'pointer', boxShadow:'0 4px 14px rgba(99,102,241,.35)' }}>
            <Plus size={16} /> Générer un rapport
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div style={{ display:'flex', alignItems:'center', gap:12, background:'#fef2f2', border:'1px solid #fecaca', borderLeft:'4px solid #ef4444', borderRadius:12, padding:'12px 16px' }}>
          <span style={{ fontSize:13, color:'#dc2626', flex:1 }}>⚠️ {error}</span>
          <button onClick={()=>setError(null)} style={{ background:'none', border:'none', cursor:'pointer', color:'#dc2626' }}><X size={16} /></button>
        </div>
      )}

      {/* Stats */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(150px,1fr))', gap:12, animation:'fadeUp .4s .05s both' }}>
        {[
          { label: isCEO?'Rapports totaux':'Mes rapports', value:reports.length,                                    color:'#6366f1', bg:'#eef2ff', border:'#c7d2fe' },
          { label:'Complétés',                              value:reports.filter(r=>r.status==='Completed').length, color:'#16a34a', bg:'#f0fdf4', border:'#bbf7d0' },
          { label:'Ce mois',                                value:thisMonth,                                        color:'#f59e0b', bg:'#fffbeb', border:'#fde68a' },
        ].map((s,i) => (
          <div key={i} style={{ background:s.bg, border:`1px solid ${s.border}`, borderRadius:12, padding:'14px 16px' }}>
            <div style={{ fontSize:26, fontWeight:800, color:s.color, lineHeight:1 }}>{s.value}</div>
            <div style={{ fontSize:11, fontWeight:600, color:'#64748b', marginTop:4 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Reports grid */}
      {reports.length === 0 ? (
        <div style={{ textAlign:'center', padding:'56px 0', background:'#fff', borderRadius:14, border:'1px solid #f1f5f9' }}>
          <FileBarChart size={48} color="#e2e8f0" style={{ margin:'0 auto 12px', display:'block' }} />
          <p style={{ color:'#94a3b8', fontSize:15, fontWeight:600 }}>Aucun rapport généré</p>
          <p style={{ color:'#cbd5e1', fontSize:13 }}>Cliquez sur "Générer un rapport" pour commencer</p>
        </div>
      ) : (
        <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(280px,1fr))', gap:14, animation:'fadeUp .4s .1s both' }}>
          {reports.map((r, i) => {
            const t  = getType(r.report_type);
            const ss = STATUS_STYLE[r.status] || STATUS_STYLE.Pending;
            const Icon = t.icon;
            let parsed = null;
            try { parsed = r.content ? JSON.parse(r.content) : null; } catch {}

            return (
              <div key={r.report_id} className="rep-card" style={{ background:'#fff', borderRadius:14, border:'1px solid #f1f5f9', overflow:'hidden', boxShadow:'0 1px 3px rgba(0,0,0,.05)', display:'flex', flexDirection:'column', animation:`fadeUp .4s ${i*.04}s both` }}>
                {/* Top strip */}
                <div style={{ height:4, background:`linear-gradient(90deg,${t.color},${t.color}66)` }} />
                <div style={{ padding:'16px 18px', flex:1 }}>
                  {/* Header */}
                  <div style={{ display:'flex', alignItems:'flex-start', justifyContent:'space-between', marginBottom:12, gap:8 }}>
                    <div style={{ width:40, height:40, borderRadius:11, background:t.bg, display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
                      <Icon size={19} color={t.color} />
                    </div>
                    <span style={{ fontSize:11, fontWeight:700, background:ss.bg, color:ss.color, border:`1px solid ${ss.border}`, borderRadius:20, padding:'2px 9px', whiteSpace:'nowrap' }}>
                      {r.status}
                    </span>
                  </div>

                  <div style={{ fontWeight:800, fontSize:14, color:'#0f172a', marginBottom:4, lineHeight:1.3 }}>{r.title}</div>
                  <div style={{ fontSize:11, fontWeight:700, color:t.color, marginBottom:10 }}>{t.label}</div>

                  <div style={{ display:'flex', alignItems:'center', gap:5, fontSize:12, color:'#94a3b8', marginBottom:8 }}>
                    <Calendar size={12} /> {fmt(r.generation_date)}
                  </div>

                  {isCEO && r.generated_by && (
                    <div style={{ fontSize:12, color:'#94a3b8', marginBottom:8 }}>
                      👤 {r.generated_by_name || r.generated_by}
                    </div>
                  )}

                  <div style={{ fontSize:12, color:'#64748b', background:'#f8fafc', borderRadius:8, padding:'8px 10px', marginBottom:10 }}>
                    <div style={{ fontWeight:600, marginBottom:3 }}>Période</div>
                    <div>{fmt(r.period_start)} → {fmt(r.period_end)}</div>
                  </div>

                  {parsed && (
                    <div style={{ display:'flex', flexWrap:'wrap', gap:6 }}>
                      {parsed.total_projects  !== undefined && <span style={{ fontSize:10, background:'#eff6ff', color:'#3b82f6', borderRadius:20, padding:'2px 9px', fontWeight:700 }}>📁 {parsed.total_projects} projets</span>}
                      {parsed.total_employees !== undefined && <span style={{ fontSize:10, background:'#f5f3ff', color:'#8b5cf6', borderRadius:20, padding:'2px 9px', fontWeight:700 }}>👥 {parsed.total_employees} employés</span>}
                      {parsed.total_tasks     !== undefined && <span style={{ fontSize:10, background:'#fffbeb', color:'#f59e0b', borderRadius:20, padding:'2px 9px', fontWeight:700 }}>✅ {parsed.total_tasks} tâches</span>}
                      {parsed.completion_rate !== undefined && <span style={{ fontSize:10, background:'#f0fdf4', color:'#16a34a', borderRadius:20, padding:'2px 9px', fontWeight:700 }}>📊 {parsed.completion_rate}%</span>}
                    </div>
                  )}
                </div>

                <div style={{ padding:'12px 18px', borderTop:'1px solid #f8fafc' }}>
                  <button onClick={()=>download(r)} disabled={r.status!=='Completed'}
                    style={{ width:'100%', display:'flex', alignItems:'center', justifyContent:'center', gap:7, padding:'9px', background: r.status==='Completed' ? '#eef2ff' : '#f8fafc', color: r.status==='Completed' ? '#4f46e5' : '#94a3b8', border:`1px solid ${r.status==='Completed'?'#c7d2fe':'#e2e8f0'}`, borderRadius:8, fontWeight:600, fontSize:13, cursor:r.status==='Completed'?'pointer':'not-allowed' }}>
                    <Download size={14} /> Télécharger
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal */}
      {modal && (
        <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.5)', zIndex:1000, display:'flex', alignItems:'center', justifyContent:'center', padding:20, backdropFilter:'blur(4px)' }} onClick={()=>setModal(false)}>
          <div style={{ background:'#fff', borderRadius:18, width:'100%', maxWidth:580, maxHeight:'90vh', overflow:'hidden', display:'flex', flexDirection:'column', boxShadow:'0 32px 80px rgba(0,0,0,.22)' }} onClick={e=>e.stopPropagation()}>

            <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'20px 28px', borderBottom:'1px solid #f1f5f9' }}>
              <div>
                <h2 style={{ fontSize:18, fontWeight:800, color:'#0f172a', margin:0 }}>📊 Générer un rapport</h2>
                <p style={{ fontSize:13, color:'#64748b', margin:'3px 0 0' }}>Sélectionnez le type et la période</p>
              </div>
              <button onClick={()=>setModal(false)} style={{ width:32, height:32, borderRadius:8, border:'1px solid #e2e8f0', background:'#f8fafc', cursor:'pointer', display:'flex', alignItems:'center', justifyContent:'center' }}>
                <X size={15} color="#64748b" />
              </button>
            </div>

            <form onSubmit={generate} style={{ overflowY:'auto', flex:1 }}>
              <div style={{ padding:'20px 28px', display:'flex', flexDirection:'column', gap:20 }}>

                {/* Report type */}
                <div>
                  <div style={{ fontSize:12, fontWeight:700, color:'#64748b', textTransform:'uppercase', letterSpacing:'0.07em', marginBottom:12 }}>Type de rapport</div>
                  <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:10 }}>
                    {reportTypes.map(t => {
                      const Icon = t.icon;
                      const sel = form.report_type === t.value;
                      return (
                        <label key={t.value} className={`rt-opt${sel?' sel':''}`} onClick={()=>setForm(f=>({...f,report_type:t.value}))}>
                          <input type="radio" name="rt" value={t.value} checked={sel} onChange={()=>{}} style={{ display:'none' }} />
                          <div style={{ width:32, height:32, borderRadius:9, background:t.bg, display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
                            <Icon size={16} color={t.color} />
                          </div>
                          <span style={{ fontWeight:700, fontSize:13, color: sel?'#4f46e5':'#374151' }}>{t.label}</span>
                        </label>
                      );
                    })}
                  </div>
                  {isManager && !isCEO && (
                    <p style={{ fontSize:12, color:'#94a3b8', marginTop:8, display:'flex', alignItems:'center', gap:4 }}>
                      <Lock size={11} /> Le rapport personnalisé est réservé au CEO.
                    </p>
                  )}
                </div>

                {/* Title */}
                <div>
                  <label style={{ display:'block', fontSize:11, fontWeight:700, color:'#64748b', textTransform:'uppercase', letterSpacing:'0.07em', marginBottom:5 }}>Titre (optionnel)</label>
                  <input type="text" value={form.title} onChange={e=>setForm(f=>({...f,title:e.target.value}))}
                    placeholder="Ex: Rapport mensuel mars 2026"
                    style={{ width:'100%', padding:'9px 12px', border:'1px solid #e2e8f0', borderRadius:8, fontSize:14, outline:'none', boxSizing:'border-box', background:'#f8fafc' }} />
                </div>

                {/* Period */}
                <div>
                  <div style={{ fontSize:11, fontWeight:700, color:'#64748b', textTransform:'uppercase', letterSpacing:'0.07em', marginBottom:10 }}>Période</div>
                  <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:12 }}>
                    {[{label:'Date de début', key:'period_start'},{label:'Date de fin', key:'period_end'}].map(f=>(
                      <div key={f.key}>
                        <label style={{ display:'block', fontSize:12, color:'#64748b', fontWeight:600, marginBottom:5 }}>{f.label} *</label>
                        <input type="date" value={form[f.key]} onChange={e=>setForm(p=>({...p,[f.key]:e.target.value}))} required
                          style={{ width:'100%', padding:'9px 12px', border:'1px solid #e2e8f0', borderRadius:8, fontSize:14, outline:'none', boxSizing:'border-box', background:'#f8fafc' }} />
                      </div>
                    ))}
                  </div>
                  <p style={{ fontSize:12, color:'#94a3b8', marginTop:8 }}>💡 Par défaut l'année en cours ({yr}) est sélectionnée.</p>
                </div>
              </div>

              <div style={{ padding:'16px 28px', borderTop:'1px solid #f1f5f9', display:'flex', gap:10 }}>
                <button type="button" onClick={()=>setModal(false)} style={{ padding:'10px 20px', borderRadius:8, border:'1px solid #e2e8f0', background:'#fff', color:'#64748b', fontWeight:600, fontSize:14, cursor:'pointer' }}>
                  Annuler
                </button>
                <button type="submit" disabled={generating} style={{ flex:1, padding:'10px', borderRadius:8, border:'none', background:'linear-gradient(135deg,#4f46e5,#6366f1)', color:'#fff', fontWeight:700, fontSize:14, cursor:generating?'not-allowed':'pointer', display:'flex', alignItems:'center', justifyContent:'center', gap:7, opacity:generating?.7:1 }}>
                  {generating ? <><RefreshCw size={14} style={{ animation:'spin .8s linear infinite' }} /> Génération...</> : <><FileBarChart size={14} /> Générer le rapport</>}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Reports;