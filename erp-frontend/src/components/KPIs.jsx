import React, { useState, useEffect, useMemo } from 'react';
import { getKPIs } from '../services/api';
import {
  TrendingUp, TrendingDown, Search, Star, Calendar, ChevronDown, ChevronUp
} from 'lucide-react';

// ─── Design tokens ────────────────────────────────────────────────────────────
const RISK = {
  High:   { bg:'#fef2f2', color:'#ef4444', border:'#fecaca', dot:'#ef4444', label:'Élevé' },
  Medium: { bg:'#fffbeb', color:'#f59e0b', border:'#fde68a', dot:'#f59e0b', label:'Moyen' },
  Low:    { bg:'#f0fdf4', color:'#16a34a', border:'#bbf7d0', dot:'#22c55e', label:'Faible' },
};

// ─── Helpers ──────────────────────────────────────────────────────────────────
const RiskBadge = ({ level }) => {
  const s = RISK[level] || RISK.Low;
  return (
    <span style={{ display:'inline-flex', alignItems:'center', gap:5, background:s.bg, color:s.color,
      border:`1px solid ${s.border}`, borderRadius:20, padding:'3px 10px', fontSize:11, fontWeight:700 }}>
      <span style={{ width:6, height:6, borderRadius:'50%', background:s.dot }} />
      {s.label}
    </span>
  );
};

const Stars = ({ score }) => (
  <div style={{ display:'flex', gap:2 }}>
    {[1,2,3,4,5].map(s => (
      <Star key={s} size={12} fill={s <= score ? '#fbbf24' : 'none'} color={s <= score ? '#fbbf24' : '#e2e8f0'} />
    ))}
  </div>
);

// ─── SVG Sparkline ────────────────────────────────────────────────────────────
const Sparkline = ({ data, color = '#6366f1', height = 40, width = 120, fill = false }) => {
  if (!data || data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((v - min) / range) * (height - 4) - 2;
    return `${x},${y}`;
  });
  const polyline = pts.join(' ');
  const area = `0,${height} ${polyline} ${width},${height}`;
  return (
    <svg width={width} height={height} style={{ display:'block', overflow:'visible' }}>
      {fill && <polygon points={area} fill={color} opacity={0.12} />}
      <polyline points={polyline} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
      {/* Last point dot */}
      {pts.length > 0 && (() => {
        const [lx, ly] = pts[pts.length-1].split(',');
        return <circle cx={lx} cy={ly} r={3} fill={color} />;
      })()}
    </svg>
  );
};

// ─── Trend indicator ─────────────────────────────────────────────────────────
const Trend = ({ values, lowerIsBetter = false }) => {
  if (!values || values.length < 2) return null;
  const first = values[0], last = values[values.length - 1];
  const delta = last - first;
  const improving = lowerIsBetter ? delta < 0 : delta > 0;
  const neutral = Math.abs(delta) < 0.01;
  if (neutral) return <span style={{ fontSize:10, color:'#94a3b8' }}>stable</span>;
  return (
    <span style={{ display:'inline-flex', alignItems:'center', gap:2, fontSize:10, fontWeight:700,
      color: improving ? '#16a34a' : '#ef4444' }}>
      {improving ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
      {Math.abs(delta).toFixed(2)}
    </span>
  );
};

// ─── Mini metric tile ─────────────────────────────────────────────────────────
const MetricTile = ({ label, latest, history, color, lowerIsBetter, unit = '', format }) => {
  const display = format ? format(latest) : `${latest}${unit}`;
  return (
    <div style={{ background:'#f8fafc', borderRadius:10, padding:'10px 12px', border:'1px solid #f1f5f9', minWidth:0 }}>
      <div style={{ fontSize:10, fontWeight:700, color:'#94a3b8', textTransform:'uppercase',
        letterSpacing:'.06em', marginBottom:6 }}>{label}</div>
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:4 }}>
        <span style={{ fontSize:18, fontWeight:800, color: color || '#0f172a' }}>{display}</span>
        <Trend values={history} lowerIsBetter={lowerIsBetter} />
      </div>
      <Sparkline data={history} color={color || '#6366f1'} width={80} height={28} fill />
    </div>
  );
};

// ─── Main component ───────────────────────────────────────────────────────────
const KPIs = () => {
  const [kpis,     setKPIs]     = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [filter,   setFilter]   = useState('all');
  const [search,   setSearch]   = useState('');
  const [expanded, setExpanded] = useState({});   // project_id → bool

  useEffect(() => { load(); }, []);

  const load = async () => {
    try {
      const res = await getKPIs();           // GET /kpis?history=true → all snapshots
      setKPIs(res.data);
    } catch(e) { console.error(e); }
    finally { setLoading(false); }
  };

  // ── Group all snapshots by project, sorted by date asc ───────────────────
  const byProject = useMemo(() => {
    const map = {};
    kpis.forEach(k => {
      const pid = k.project_id;
      if (!map[pid]) map[pid] = { project_id: pid, project_name: k.project_name || pid, snapshots: [] };
      map[pid].snapshots.push(k);
    });
    // Sort snapshots by date asc within each project
    Object.values(map).forEach(p => {
      p.snapshots.sort((a, b) => a.kpi_date.localeCompare(b.kpi_date));
      p.latest = p.snapshots[p.snapshots.length - 1];   // most recent
      p.oldest = p.snapshots[0];
    });
    return Object.values(map);
  }, [kpis]);

  // ── Filter ────────────────────────────────────────────────────────────────
  const filtered = useMemo(() => byProject.filter(p => {
    const k = p.latest;
    const matchFilter =
      filter === 'all'        ? true :
      filter === 'delayed'    ? (k.schedule_variance_days || 0) > 0 :
      filter === 'overbudget' ? (k.budget_variance_percentage || 0) > 0 :
      filter === 'risk'       ? k.risk_level === 'High' : true;
    const matchSearch = !search ||
      p.project_name.toLowerCase().includes(search.toLowerCase()) ||
      p.project_id.toLowerCase().includes(search.toLowerCase());
    return matchFilter && matchSearch;
  }), [byProject, filter, search]);

  // ── Summary KPIs (based on latest snapshot of each project) ──────────────
  const summaryProjects = byProject.map(p => p.latest);
  const avgQuality    = summaryProjects.length
    ? (summaryProjects.reduce((s, k) => s + (parseFloat(k.quality_score) || 0), 0) / summaryProjects.length).toFixed(0) : 0;
  const totalInc      = summaryProjects.reduce((s, k) => s + (k.safety_incidents || 0), 0);
  const avgSat        = summaryProjects.length
    ? (summaryProjects.reduce((s, k) => s + (parseFloat(k.client_satisfaction_score) || 0), 0) / summaryProjects.length).toFixed(1) : 0;
  const highRiskCount = summaryProjects.filter(k => k.risk_level === 'High').length;
  const delayedCount  = summaryProjects.filter(k => (k.schedule_variance_days || 0) > 0).length;

  const FILTERS = [
    { key:'all',        label:'Tous',         count: byProject.length },
    { key:'delayed',    label:'En retard',    count: delayedCount },
    { key:'overbudget', label:'Hors budget',  count: byProject.filter(p => (p.latest.budget_variance_percentage || 0) > 0).length },
    { key:'risk',       label:'Risque élevé', count: highRiskCount },
  ];

  if (loading) return (
    <div style={{ display:'flex', alignItems:'center', justifyContent:'center', height:300, gap:12 }}>
      <div style={{ width:36, height:36, border:'3px solid #e2e8f0', borderTop:'3px solid #6366f1',
        borderRadius:'50%', animation:'spin .8s linear infinite' }} />
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:20, fontFamily:"'Segoe UI',system-ui,sans-serif" }}>
      <style>{`
        @keyframes spin    { to { transform:rotate(360deg) } }
        @keyframes fadeUp  { from{opacity:0;transform:translateY(12px)} to{opacity:1;transform:none} }
        .kpi-card { transition:box-shadow .18s,transform .18s; }
        .kpi-card:hover { box-shadow:0 8px 28px rgba(99,102,241,.12)!important; transform:translateY(-2px); }
        .filt-btn { border:none; cursor:pointer; font-weight:600; font-size:13px; border-radius:8px; padding:8px 14px; transition:all .15s; }
        .snap-row:hover { background:#f8fafc !important; }
        .expand-btn { background:none; border:none; cursor:pointer; color:#94a3b8; display:flex; align-items:center; gap:4px; font-size:12px; font-weight:600; padding:0; }
        .expand-btn:hover { color:#6366f1; }
      `}</style>

      {/* ── Header ── */}
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between',
        flexWrap:'wrap', gap:12, animation:'fadeUp .4s both' }}>
        <div>
          <h1 style={{ fontSize:26, fontWeight:800, color:'#0f172a', margin:0, letterSpacing:'-0.02em' }}>KPIs</h1>
          <p style={{ color:'#64748b', fontSize:14, margin:'4px 0 0' }}>
            {filtered.length} projet{filtered.length > 1 ? 's' : ''} · snapshot le plus récent affiché
          </p>
        </div>
        <div style={{ position:'relative' }}>
          <Search size={14} style={{ position:'absolute', left:10, top:'50%', transform:'translateY(-50%)', color:'#94a3b8' }} />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Rechercher..."
            style={{ padding:'9px 12px 9px 32px', border:'1px solid #e2e8f0', borderRadius:8,
              fontSize:14, background:'#f8fafc', width:200, outline:'none' }} />
        </div>
      </div>

      {/* ── Summary tiles ── */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(150px,1fr))',
        gap:12, animation:'fadeUp .4s .05s both' }}>
        {[
          { label:'Qualité moyenne',   value:`${avgQuality}/100`, color:'#6366f1', bg:'#eef2ff', border:'#c7d2fe' },
          { label:'Incidents sécu.',   value: totalInc,           color: totalInc>0?'#ef4444':'#16a34a', bg: totalInc>0?'#fef2f2':'#f0fdf4', border: totalInc>0?'#fecaca':'#bbf7d0' },
          { label:'Satisfaction moy.', value:`${avgSat}/5`,       color:'#f59e0b', bg:'#fffbeb', border:'#fde68a' },
          { label:'Risque élevé',      value: highRiskCount,      color:'#ef4444', bg:'#fef2f2', border:'#fecaca' },
          { label:'En retard',         value: delayedCount,       color:'#f97316', bg:'#fff7ed', border:'#fed7aa' },
        ].map((s, i) => (
          <div key={i} style={{ background:s.bg, border:`1px solid ${s.border}`, borderRadius:12, padding:'14px 16px' }}>
            <div style={{ fontSize:22, fontWeight:800, color:s.color, lineHeight:1 }}>{s.value}</div>
            <div style={{ fontSize:11, fontWeight:600, color:'#64748b', marginTop:4 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* ── Filter tabs ── */}
      <div style={{ display:'flex', gap:8, flexWrap:'wrap', animation:'fadeUp .4s .1s both' }}>
        {FILTERS.map(f => (
          <button key={f.key} className="filt-btn" onClick={() => setFilter(f.key)}
            style={{ background: filter===f.key ? 'linear-gradient(135deg,#4f46e5,#6366f1)' : '#fff',
              color: filter===f.key ? '#fff' : '#64748b',
              boxShadow: filter===f.key ? '0 4px 12px rgba(99,102,241,.25)' : 'none',
              border: filter===f.key ? 'none' : '1px solid #e2e8f0' }}>
            {f.label}
            <span style={{ marginLeft:6, background: filter===f.key?'rgba(255,255,255,.25)':'#f1f5f9',
              color: filter===f.key?'#fff':'#64748b', borderRadius:20, padding:'1px 7px', fontSize:11, fontWeight:800 }}>
              {f.count}
            </span>
          </button>
        ))}
      </div>

      {/* ── Project KPI cards ── */}
      <div style={{ display:'flex', flexDirection:'column', gap:14, animation:'fadeUp .4s .15s both' }}>
        {filtered.length === 0 && (
          <div style={{ textAlign:'center', padding:'48px 0', background:'#fff',
            borderRadius:14, border:'1px solid #f1f5f9' }}>
            <p style={{ color:'#94a3b8', fontSize:15, fontWeight:600 }}>Aucun KPI correspondant</p>
          </div>
        )}

        {filtered.map((project, i) => {
          const k        = project.latest;
          const snaps    = project.snapshots;
          const isOpen   = !!expanded[project.project_id];

          const budVar   = parseFloat(k.budget_variance_percentage) || 0;
          const schVar   = parseInt(k.schedule_variance_days) || 0;
          const cpi      = parseFloat(k.cost_performance_index) || 0;
          const spi      = parseFloat(k.schedule_performance_index) || 0;

          // History arrays for sparklines
          const cpiHist  = snaps.map(s => parseFloat(s.cost_performance_index) || 0);
          const spiHist  = snaps.map(s => parseFloat(s.schedule_performance_index) || 0);
          const budHist  = snaps.map(s => parseFloat(s.budget_variance_percentage) || 0);
          const delHist  = snaps.map(s => parseInt(s.schedule_variance_days) || 0);
          const qualHist = snaps.map(s => parseFloat(s.quality_score) || 0);
          const satHist  = snaps.map(s => parseFloat(s.client_satisfaction_score) || 0);

          const qualColor = (parseFloat(k.quality_score)||0) >= 90 ? '#16a34a' : (parseFloat(k.quality_score)||0) >= 75 ? '#f59e0b' : '#ef4444';

          return (
            <div key={project.project_id} className="kpi-card"
              style={{ background:'#fff', borderRadius:14, border:'1px solid #f1f5f9',
                boxShadow:'0 1px 3px rgba(0,0,0,.05)', overflow:'hidden',
                animation:`fadeUp .4s ${i * .04}s both` }}>

              {/* ── Card header ── */}
              <div style={{ padding:'18px 22px' }}>
                <div style={{ display:'flex', alignItems:'flex-start', justifyContent:'space-between',
                  marginBottom:16, gap:12, flexWrap:'wrap' }}>
                  <div>
                    <div style={{ fontWeight:800, fontSize:16, color:'#0f172a', marginBottom:3 }}>
                      {project.project_name}
                    </div>
                    <div style={{ fontSize:12, color:'#94a3b8', display:'flex', alignItems:'center', gap:8 }}>
                      <span>{project.project_id}</span>
                      <span>·</span>
                      <Calendar size={11} />
                      <span>{k.kpi_date}</span>
                      <span>·</span>
                      <span style={{ color:'#6366f1', fontWeight:600 }}>{snaps.length} snapshot{snaps.length > 1 ? 's' : ''}</span>
                    </div>
                  </div>
                  <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                    <RiskBadge level={k.risk_level} />
                    <button className="expand-btn" onClick={() => setExpanded(prev => ({ ...prev, [project.project_id]: !isOpen }))}>
                      {isOpen ? <><ChevronUp size={14} /> Masquer</> : <><ChevronDown size={14} /> Historique</>}
                    </button>
                  </div>
                </div>

                {/* ── 6 metric tiles with sparklines ── */}
                <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(140px,1fr))', gap:10 }}>

                  {/* CPI */}
                  <MetricTile
                    label="CPI"
                    latest={cpi.toFixed(3)}
                    history={cpiHist}
                    color={cpi >= 1 ? '#16a34a' : '#ef4444'}
                    lowerIsBetter={false}
                  />

                  {/* SPI */}
                  <MetricTile
                    label="SPI"
                    latest={spi.toFixed(3)}
                    history={spiHist}
                    color={spi >= 1 ? '#16a34a' : '#f59e0b'}
                    lowerIsBetter={false}
                  />

                  {/* Budget Δ */}
                  <MetricTile
                    label="Budget Δ"
                    latest={`${budVar > 0 ? '+' : ''}${budVar}%`}
                    history={budHist}
                    color={budVar > 0 ? '#ef4444' : '#16a34a'}
                    lowerIsBetter={true}
                  />

                  {/* Retard */}
                  <MetricTile
                    label="Retard"
                    latest={`${schVar > 0 ? '+' : ''}${schVar}j`}
                    history={delHist}
                    color={schVar > 10 ? '#f97316' : schVar > 0 ? '#f59e0b' : '#16a34a'}
                    lowerIsBetter={true}
                  />

                  {/* Qualité */}
                  <MetricTile
                    label="Qualité"
                    latest={parseFloat(k.quality_score || 0).toFixed(1)}
                    history={qualHist}
                    color={qualColor}
                    lowerIsBetter={false}
                    unit="/100"
                  />

                  {/* Satisfaction */}
                  <div style={{ background:'#fffbeb', borderRadius:10, padding:'10px 12px', border:'1px solid #fde68a', minWidth:0 }}>
                    <div style={{ fontSize:10, fontWeight:700, color:'#94a3b8', textTransform:'uppercase',
                      letterSpacing:'.06em', marginBottom:6 }}>Satisfaction</div>
                    <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:4 }}>
                      <Stars score={Math.round(parseFloat(k.client_satisfaction_score || 0))} />
                      <Trend values={satHist} lowerIsBetter={false} />
                    </div>
                    <Sparkline data={satHist} color="#f59e0b" width={80} height={28} fill />
                  </div>
                </div>
              </div>

              {/* ── Expandable snapshot table ── */}
              {isOpen && (
                <div style={{ borderTop:'1px solid #f1f5f9', background:'#f8fafc' }}>
                  <div style={{ overflowX:'auto' }}>
                    <table style={{ width:'100%', borderCollapse:'collapse', fontSize:12 }}>
                      <thead>
                        <tr style={{ background:'#f1f5f9' }}>
                          {['Date','Budget Δ','Retard','CPI','SPI','Qualité','Incidents','Satisfaction','Risque'].map(h => (
                            <th key={h} style={{ padding:'8px 14px', textAlign:'left', fontWeight:700,
                              color:'#64748b', fontSize:11, textTransform:'uppercase', letterSpacing:'.05em',
                              whiteSpace:'nowrap' }}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {/* Show all snapshots, newest first */}
                        {[...snaps].reverse().map((s, si) => {
                          const isLatest = si === 0;
                          const bv = parseFloat(s.budget_variance_percentage) || 0;
                          const sv = parseInt(s.schedule_variance_days) || 0;
                          const c  = parseFloat(s.cost_performance_index) || 0;
                          const sp = parseFloat(s.schedule_performance_index) || 0;
                          return (
                            <tr key={s.kpi_id || si} className="snap-row"
                              style={{ background: isLatest ? '#eef2ff' : 'transparent',
                                borderBottom:'1px solid #f1f5f9' }}>
                              <td style={{ padding:'8px 14px', fontWeight: isLatest ? 700 : 400,
                                color: isLatest ? '#4f46e5' : '#374151', whiteSpace:'nowrap' }}>
                                {s.kpi_date}
                                {isLatest && <span style={{ marginLeft:6, fontSize:10, background:'#6366f1',
                                  color:'#fff', borderRadius:4, padding:'1px 5px' }}>récent</span>}
                              </td>
                              <td style={{ padding:'8px 14px', color: bv > 0 ? '#ef4444' : '#16a34a', fontWeight:600 }}>
                                {bv > 0 ? '+' : ''}{bv}%
                              </td>
                              <td style={{ padding:'8px 14px', color: sv > 0 ? '#f97316' : '#16a34a', fontWeight:600 }}>
                                {sv > 0 ? '+' : ''}{sv}j
                              </td>
                              <td style={{ padding:'8px 14px', color: c >= 1 ? '#16a34a' : '#ef4444', fontWeight:700 }}>
                                {c.toFixed(3)}
                              </td>
                              <td style={{ padding:'8px 14px', color: sp >= 1 ? '#16a34a' : '#f59e0b', fontWeight:700 }}>
                                {sp.toFixed(3)}
                              </td>
                              <td style={{ padding:'8px 14px', color:'#374151' }}>
                                {parseFloat(s.quality_score || 0).toFixed(1)}
                              </td>
                              <td style={{ padding:'8px 14px', color: s.safety_incidents > 0 ? '#ef4444' : '#16a34a',
                                fontWeight: s.safety_incidents > 0 ? 700 : 400 }}>
                                {s.safety_incidents || 0}
                              </td>
                              <td style={{ padding:'8px 14px' }}>
                                <Stars score={Math.round(parseFloat(s.client_satisfaction_score || 0))} />
                              </td>
                              <td style={{ padding:'8px 14px' }}>
                                <RiskBadge level={s.risk_level} />
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default KPIs;