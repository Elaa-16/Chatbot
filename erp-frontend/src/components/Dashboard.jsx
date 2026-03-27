import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api, { getStats, getProjects, getKPIs } from '../services/api';
import { useNavigate } from 'react-router-dom';
import {
  TrendingUp, TrendingDown, Briefcase, DollarSign,
  Target, AlertCircle, CheckCircle,
  MapPin, BarChart2, ArrowRight, Activity,
  Zap, ChevronRight
} from 'lucide-react';

// ── Mini sparkline ────────────────────────────────────────────────────────────
const Sparkline = ({ values, color, height = 36 }) => {
  if (!values?.length) return null;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = max - min || 1;
  const w = 80, h = height;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w;
    const y = h - ((v - min) / range) * (h - 4) - 2;
    return `${x},${y}`;
  }).join(' ');
  const areaBottom = `${w},${h} 0,${h}`;
  return (
    <svg width={w} height={h} style={{ overflow: 'visible' }}>
      <defs>
        <linearGradient id={`sg-${color.replace('#','')}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.25" />
          <stop offset="100%" stopColor={color} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      <polygon points={`${pts} ${areaBottom}`} fill={`url(#sg-${color.replace('#','')})`} />
      <polyline points={pts} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={pts.split(' ').pop().split(',')[0]} cy={pts.split(' ').pop().split(',')[1]} r="3" fill={color} />
    </svg>
  );
};

// ── Risk badge ────────────────────────────────────────────────────────────────
const RiskBadge = ({ level }) => {
  const map = {
    High:   { bg: '#fef2f2', color: '#ef4444', dot: '#ef4444', label: 'Élevé' },
    Medium: { bg: '#fffbeb', color: '#f59e0b', dot: '#f59e0b', label: 'Moyen' },
    Low:    { bg: '#f0fdf4', color: '#22c55e', dot: '#22c55e', label: 'Faible' },
  };
  const s = map[level] || map.Low;
  return (
    <span style={{ display:'inline-flex', alignItems:'center', gap:4, background:s.bg, color:s.color, borderRadius:20, padding:'2px 9px', fontSize:11, fontWeight:700 }}>
      <span style={{ width:5, height:5, borderRadius:'50%', background:s.dot, display:'inline-block' }} />
      {s.label}
    </span>
  );
};

// ── Status pill ───────────────────────────────────────────────────────────────
const StatusPill = ({ status }) => {
  const map = {
    'In Progress': { bg:'#eff6ff', color:'#3b82f6', label:'En cours' },
    'Completed':   { bg:'#f0fdf4', color:'#22c55e', label:'Terminé' },
    'Planning':    { bg:'#faf5ff', color:'#a855f7', label:'Planifié' },
  };
  const s = map[status] || { bg:'#f8fafc', color:'#64748b', label: status };
  return <span style={{ background:s.bg, color:s.color, borderRadius:20, padding:'2px 9px', fontSize:10, fontWeight:700 }}>{s.label}</span>;
};

// ── Admin Dashboard ──────────────────────────────────────────────────────────
const AdminDashboard = () => {
  const [stats, setStats]     = useState({ users: 0, apis: 0, logs: 0 });
  const [recentLogs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [empRes, whiteRes, logRes] = await Promise.all([
          api.get('/employees'),
          api.get('/whitelist'),
          api.get('/activity-logs', { params: { limit: 8 } })
        ]);
        setStats({ users: empRes.data.length, apis: whiteRes.data.length, logs: logRes.data.length });
        setLogs(logRes.data.slice(0, 8));
      } catch (err) { console.error(err); }
      finally { setLoading(false); }
    };
    fetchData();
  }, []);

  const actionColors = {
    login:  { bg: '#fef3c7', text: '#b45309', dot: '#f59e0b', label: 'Connexion' },
    prompt: { bg: '#e0e7ff', text: '#4338ca', dot: '#6366f1', label: 'Prompt IA' },
    create: { bg: '#dcfce7', text: '#15803d', dot: '#22c55e', label: 'Création' },
    update: { bg: '#dbeafe', text: '#1d4ed8', dot: '#3b82f6', label: 'MAJ' },
    delete: { bg: '#fee2e2', text: '#b91c1c', dot: '#ef4444', label: 'Suppression' },
  };
  const getAction = t => actionColors[t] || { bg: '#f1f5f9', text: '#475569', dot: '#94a3b8', label: t };

  const timeAgo = d => {
    if (!d) return '—';
    const diff = Date.now() - new Date(d);
    const m = Math.floor(diff/60000), h = Math.floor(diff/3600000);
    if (m < 1) return 'À l\'instant';
    if (m < 60) return `Il y a ${m} min`;
    if (h < 24) return `Il y a ${h}h`;
    return new Date(d).toLocaleDateString('fr-FR', { day:'numeric', month:'short' });
  };

  const statCards = [
    { label: 'Utilisateurs', value: stats.users, gradient: 'linear-gradient(135deg,#6366f1,#4f46e5)', icon: '👥', path: '/employees', hint: 'Gérer les comptes' },
    { label: 'APIs Surveillées', value: stats.apis, gradient: 'linear-gradient(135deg,#0ea5e9,#0284c7)', icon: '🔗', path: '/whitelist', hint: 'Liste blanche' },
    { label: 'Opérations Récentes', value: stats.logs, gradient: 'linear-gradient(135deg,#10b981,#059669)', icon: '📋', path: '/logs', hint: 'Dernières 8 opérations loguées' },
  ];

  const quickActions = [
    { label: 'Ajouter un Utilisateur', icon: '➕', path: '/employees', color: '#6366f1' },
    { label: 'Journaux d\'Audit', icon: '📄', path: '/logs', color: '#0ea5e9' },
    { label: 'Liste Blanche API', icon: '🛡️', path: '/whitelist', color: '#10b981' },
    { label: 'Notifications', icon: '🔔', path: '/notifications', color: '#f59e0b' },
  ];

  if (loading) return (
    <div style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', height:300, gap:16 }}>
      <div style={{ width:40, height:40, border:'3px solid #e2e8f0', borderTop:'3px solid #6366f1', borderRadius:'50%', animation:'spin 0.8s linear infinite' }} />
      <p style={{ color:'#64748b', fontSize:14 }}>Chargement...</p>
    </div>
  );

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:24, fontFamily:"'Segoe UI',system-ui,sans-serif" }}>
      <style>{`
        @keyframes spin   { to { transform: rotate(360deg); } }
        @keyframes fadeUp { from { opacity:0; transform:translateY(16px); } to { opacity:1; transform:translateY(0); } }
        .adm-card { transition: box-shadow 0.2s, transform 0.2s; }
        .adm-card:hover { transform: translateY(-4px); box-shadow: 0 12px 32px rgba(0,0,0,0.15) !important; }
        .adm-qa { transition: all 0.15s; cursor:pointer; }
        .adm-qa:hover { transform: translateX(4px); background:#f8fafc !important; }
      `}</style>

      {/* Hero Banner */}
      <div style={{ background:'linear-gradient(135deg,#1e1b4b 0%,#312e81 45%,#4338ca 80%,#6366f1 100%)', borderRadius:20, padding:'28px 32px', position:'relative', overflow:'hidden', animation:'fadeUp 0.5s ease both' }}>
        <div style={{ position:'absolute', top:-40, right:-40, width:200, height:200, borderRadius:'50%', background:'rgba(255,255,255,0.05)' }} />
        <div style={{ position:'absolute', bottom:-60, left:120, width:160, height:160, borderRadius:'50%', background:'rgba(255,255,255,0.04)' }} />
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', flexWrap:'wrap', gap:16, position:'relative' }}>
          <div>
            <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:8 }}>
              <span style={{ fontSize:28 }}>🛡️</span>
              <span style={{ background:'rgba(255,255,255,0.15)', color:'#c7d2fe', borderRadius:20, padding:'3px 12px', fontSize:12, fontWeight:700, letterSpacing:'0.06em' }}>ADMIN</span>
            </div>
            <h1 style={{ fontSize:28, fontWeight:800, color:'#fff', margin:'0 0 6px 0', letterSpacing:'-0.02em' }}>Espace Administrateur</h1>
            <p style={{ color:'rgba(255,255,255,0.65)', fontSize:14, margin:0 }}>Supervision du système, gestion des utilisateurs & audit de sécurité</p>
          </div>
          <div style={{ display:'flex', gap:12, flexWrap:'wrap' }}>
            {quickActions.map((qa, i) => (
              <button key={i} onClick={() => navigate(qa.path)} className="adm-qa"
                style={{ display:'flex', alignItems:'center', gap:7, background:'rgba(255,255,255,0.12)', backdropFilter:'blur(8px)', border:'1px solid rgba(255,255,255,0.2)', borderRadius:10, color:'#fff', padding:'9px 14px', fontSize:13, fontWeight:600 }}>
                <span>{qa.icon}</span>{qa.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Stat Cards */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(240px,1fr))', gap:20, animation:'fadeUp 0.5s 0.1s ease both' }}>
        {statCards.map((c, i) => (
          <div key={i} className="adm-card" onClick={() => navigate(c.path)}
            style={{ background:c.gradient, borderRadius:18, padding:28, cursor:'pointer', boxShadow:'0 8px 24px rgba(0,0,0,0.12)', position:'relative', overflow:'hidden' }}>
            <div style={{ position:'absolute', top:-20, right:-20, width:100, height:100, borderRadius:'50%', background:'rgba(255,255,255,0.1)' }} />
            <div style={{ fontSize:36, marginBottom:8 }}>{c.icon}</div>
            <div style={{ fontSize:48, fontWeight:900, color:'#fff', lineHeight:1, marginBottom:6 }}>{c.value}</div>
            <div style={{ fontSize:15, fontWeight:700, color:'rgba(255,255,255,0.9)', marginBottom:4 }}>{c.label}</div>
            <div style={{ fontSize:12, color:'rgba(255,255,255,0.6)' }}>{c.hint} →</div>
          </div>
        ))}
      </div>

      {/* Activity Feed */}
      <div style={{ background:'#fff', borderRadius:18, border:'1px solid #e2e8f0', boxShadow:'0 4px 12px rgba(0,0,0,0.04)', overflow:'hidden', animation:'fadeUp 0.5s 0.2s ease both' }}>
        <div style={{ padding:'20px 24px', borderBottom:'1px solid #f1f5f9', display:'flex', alignItems:'center', justifyContent:'space-between' }}>
          <div>
            <h2 style={{ fontSize:18, fontWeight:800, color:'#0f172a', margin:0 }}>Activité Récente</h2>
            <p style={{ color:'#94a3b8', fontSize:13, margin:'2px 0 0' }}>Dernières opérations enregistrées dans le système</p>
          </div>
          <button onClick={() => navigate('/logs')} style={{ background:'#eef2ff', color:'#4f46e5', border:'none', borderRadius:8, padding:'7px 14px', fontWeight:700, fontSize:13, cursor:'pointer' }}>
            Voir tout →
          </button>
        </div>
        <div style={{ padding:'8px 0' }}>
          {recentLogs.length === 0 && (
            <div style={{ textAlign:'center', padding:'32px 0', color:'#94a3b8', fontSize:14 }}>Aucune activité récente.</div>
          )}
          {recentLogs.map((log, i) => {
            const a = getAction(log.action_type);
            return (
              <div key={i} style={{ display:'flex', alignItems:'center', gap:16, padding:'14px 24px', borderBottom: i < recentLogs.length - 1 ? '1px solid #f8fafc' : 'none' }}>
                <div style={{ width:38, height:38, borderRadius:12, background:a.bg, display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
                  <div style={{ width:10, height:10, borderRadius:'50%', background:a.dot }} />
                </div>
                <div style={{ flex:1, minWidth:0 }}>
                  <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:3 }}>
                    <span style={{ background:a.bg, color:a.text, fontSize:11, fontWeight:700, padding:'2px 8px', borderRadius:20 }}>{a.label}</span>
                    <span style={{ fontSize:13, fontWeight:600, color:'#334155' }}>{log.user_id}</span>
                  </div>
                  <div style={{ fontSize:12, color:'#64748b', whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis' }}>{log.details || '—'}</div>
                </div>
                <div style={{ fontSize:11, color:'#94a3b8', whiteSpace:'nowrap', flexShrink:0 }}>{timeAgo(log.timestamp)}</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

// ── Main Dashboard ────────────────────────────────────────────────────────────
const Dashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats]       = useState(null);
  const [projects, setProjects] = useState([]);
  const [kpis, setKPIs]         = useState([]);
  const [loading, setLoading]   = useState(true);
  const [visible, setVisible]   = useState(false);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { if (user?.role !== 'admin') loadData(); }, [user]);

  const loadData = async () => {
    try {
      const [sR, pR, kR] = await Promise.all([getStats(), getProjects(), getKPIs()]);
      setStats(sR.data);
      setProjects(pR.data);
      setKPIs(kR.data);
      setTimeout(() => setVisible(true), 50);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  // ── Derived metrics ──────────────────────────────────────────────────────
  const budgetVariance = stats?.total_budget && stats?.total_actual_cost
    ? ((stats.total_actual_cost - stats.total_budget) / stats.total_budget * 100).toFixed(1)
    : 0;

  const uniqueKpis = kpis.filter((k, i, arr) =>
    arr.findIndex(x => x.project_id === k.project_id) === i
  );

  const delayedProjects   = uniqueKpis.filter(k => (k.schedule_variance_days || 0) > 0).length;
  const completedProjects = projects.filter(p => p.status === 'Completed').length;
  const inProgressCount   = projects.filter(p => p.status === 'In Progress').length;
  const onTrackProjects   = inProgressCount - delayedProjects;
  const criticalProjects  = uniqueKpis.filter(k => (k.schedule_variance_days || 0) > 30).length;
  const hasAlerts         = kpis.some(k => k.safety_incidents > 2 || k.quality_score < 85);



  const topDelayed = [...uniqueKpis]
    .filter(k => (k.schedule_variance_days || 0) > 0)
    .sort((a, b) => (b.schedule_variance_days || 0) - (a.schedule_variance_days || 0))
    .slice(0, 3);

  // fake sparklines for visual richness
  const budgetSparkline   = [82, 85, 83, 88, 91, 89, 94, 92, 96, 100];
  const progressSparkline = [30, 38, 45, 42, 50, 55, 53, 58, 62, stats?.avg_completion || 60];


  const roleLabel = { ceo: 'CEO', manager: 'Manager', employee: 'Employé', rh: 'RH' };

  // ── Admin: render after hooks ─────────────────────────────────────────────
  if (user?.role === 'admin') return <AdminDashboard />;

  // ── Loading ──────────────────────────────────────────────────────────────
  if (loading) return (
    <div style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', height:300, gap:16 }}>
      <div style={{ width:40, height:40, border:'3px solid #e2e8f0', borderTop:'3px solid #6366f1', borderRadius:'50%', animation:'spin 0.8s linear infinite' }} />
      <p style={{ color:'#64748b', fontSize:14 }}>Chargement...</p>
      <style>{`@keyframes spin { to { transform:rotate(360deg); } }`}</style>
    </div>
  );

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:20, fontFamily:"'Segoe UI', system-ui, sans-serif" }}>
      <style>{`
        @keyframes spin   { to { transform: rotate(360deg); } }
        @keyframes fadeUp { from { opacity:0; transform:translateY(16px); } to { opacity:1; transform:translateY(0); } }
        @keyframes pulse  { 0%,100% { opacity:1; } 50% { opacity:0.5; } }
        .dash-card { transition: box-shadow 0.2s, transform 0.2s; }
        .dash-card:hover { box-shadow: 0 8px 28px rgba(99,102,241,0.13) !important; transform: translateY(-2px); }
        .proj-row { transition: background 0.15s; }
        .proj-row:hover { background: #f0f4ff !important; }
        .nav-btn { transition: all 0.15s; }
        .nav-btn:hover { background: #eef2ff !important; color: #4f46e5 !important; }
      `}</style>

      {/* ── Hero header ── */}
      <div style={{ opacity: visible ? 1 : 0, animation: visible ? 'fadeUp 0.5s ease both' : 'none' }}>
        <div style={{
          background: 'linear-gradient(135deg, #1e1b4b 0%, #312e81 40%, #4338ca 70%, #6366f1 100%)',
          borderRadius: 20, padding: '28px 32px', position: 'relative', overflow: 'hidden',
          boxShadow: '0 8px 32px rgba(99,102,241,0.3)',
        }}>
          {/* Background decoration */}
          <div style={{ position:'absolute', top:-60, right:-60, width:220, height:220, borderRadius:'50%', background:'rgba(255,255,255,0.05)' }} />
          <div style={{ position:'absolute', bottom:-40, right:120, width:150, height:150, borderRadius:'50%', background:'rgba(255,255,255,0.04)' }} />
          <div style={{ position:'absolute', top:20, right:200, width:6, height:6, borderRadius:'50%', background:'rgba(255,255,255,0.4)', animation:'pulse 2s infinite' }} />
          <div style={{ position:'absolute', top:50, right:160, width:4, height:4, borderRadius:'50%', background:'rgba(255,255,255,0.3)', animation:'pulse 2.5s infinite 0.5s' }} />

          <div style={{ position:'relative', zIndex:1, display:'flex', alignItems:'center', justifyContent:'space-between', flexWrap:'wrap', gap:16 }}>
            <div style={{ display:'flex', alignItems:'center', gap:16 }}>
              <div style={{ width:56, height:56, borderRadius:15, background:'rgba(255,255,255,0.15)', border:'1.5px solid rgba(255,255,255,0.25)', display:'flex', alignItems:'center', justifyContent:'center', fontSize:20, fontWeight:800, color:'#fff', flexShrink:0 }}>
                {user?.first_name?.[0]}{user?.last_name?.[0]}
              </div>
              <div>
                <p style={{ color:'rgba(255,255,255,0.65)', fontSize:12, fontWeight:600, letterSpacing:'0.1em', textTransform:'uppercase', margin:0 }}>
                  Tableau de bord — {roleLabel[user?.role] || 'Utilisateur'}
                </p>
                <h1 style={{ color:'#fff', fontSize:22, fontWeight:800, margin:'4px 0 0', letterSpacing:'-0.02em' }}>
                  Bonjour, {user?.first_name} ! 👋
                </h1>
                <p style={{ color:'rgba(255,255,255,0.6)', fontSize:13, margin:'4px 0 0' }}>
                  {new Date().toLocaleDateString('fr-FR', { weekday:'long', year:'numeric', month:'long', day:'numeric' })}
                </p>
              </div>
            </div>


          </div>
        </div>
      </div>

      {/* ── Alert ── */}
      {hasAlerts && user?.role !== 'manager' && (
        <div style={{ display:'flex', alignItems:'center', gap:12, background:'#fef2f2', border:'1px solid #fecaca', borderLeft:'4px solid #ef4444', borderRadius:12, padding:'14px 18px', animation:'fadeUp 0.5s 0.1s both' }}>
          <AlertCircle size={18} color="#dc2626" style={{ flexShrink:0 }} />
          <div>
            <strong style={{ color:'#991b1b', fontSize:14 }}>⚠️ Alertes KPI détectées</strong>
            <p style={{ color:'#b91c1c', fontSize:13, margin:'3px 0 0' }}>Certains projets ont des incidents de sécurité ou scores de qualité critiques.</p>
          </div>
          <button className="nav-btn" onClick={() => navigate('/kpis')} style={{ marginLeft:'auto', display:'flex', alignItems:'center', gap:5, background:'#fef2f2', border:'1px solid #fecaca', borderRadius:8, padding:'6px 12px', color:'#dc2626', fontWeight:600, fontSize:12, cursor:'pointer', flexShrink:0 }}>
            Voir KPIs <ChevronRight size={12} />
          </button>
        </div>
      )}

      {hasAlerts && user?.role === 'manager' && (
        <div style={{ display:'flex', alignItems:'center', gap:12, background:'#fef2f2', border:'1px solid #fecaca', borderLeft:'4px solid #ef4444', borderRadius:12, padding:'14px 18px', animation:'fadeUp 0.5s 0.1s both' }}>
          <AlertCircle size={18} color="#dc2626" style={{ flexShrink:0 }} />
          <div>
            <strong style={{ color:'#991b1b', fontSize:14 }}>⚠️ Tâches bloquées</strong>
            <p style={{ color:'#b91c1c', fontSize:13, margin:'3px 0 0' }}>Des membres de votre équipe ont des tâches bloquées nécessitant votre attention.</p>
          </div>
          <button className="nav-btn" onClick={() => navigate('/tasks')} style={{ marginLeft:'auto', display:'flex', alignItems:'center', gap:5, background:'#fef2f2', border:'1px solid #fecaca', borderRadius:8, padding:'6px 12px', color:'#dc2626', fontWeight:600, fontSize:12, cursor:'pointer', flexShrink:0 }}>
            Voir Tâches <ChevronRight size={12} />
          </button>
        </div>
      )}

      {/* ── Stat cards ── */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:14, animation:'fadeUp 0.5s 0.15s both' }}>
        {[
          {
            label: 'Budget Total',
            raw: stats?.total_budget,
            display: `${((stats?.total_budget||0)/1_000_000).toFixed(1)}M TND`,
            sub: `Coût réel : ${((stats?.total_actual_cost||0)/1_000_000).toFixed(1)}M TND`,
            icon: <DollarSign size={20} />,
            accent: '#10b981', bg: '#ecfdf5', border: '#bbf7d0',
            spark: budgetSparkline,
          },
          {
            label: 'Projets En Cours',
            display: inProgressCount,
            sub: `${completedProjects} terminé${completedProjects>1?'s':''}`,
            icon: <Briefcase size={20} />,
            accent: '#6366f1', bg: '#eef2ff', border: '#c7d2fe',
            spark: [3,4,4,5,6,6,7,8,inProgressCount,inProgressCount],
          },
          {
            label: 'Avancement Moyen',
            display: `${(stats?.avg_completion||0).toFixed(1)}%`,
            sub: `${onTrackProjects} projet${onTrackProjects>1?'s':''} en bonne voie`,
            icon: <Target size={20} />,
            accent: '#8b5cf6', bg: '#f5f3ff', border: '#ddd6fe',
            spark: progressSparkline,
          },
          {
            label: budgetVariance < 0 ? '✅ Budget OK' : '⚠️ Dépassement',
            display: `${Math.abs(budgetVariance)}%`,
            sub: budgetVariance < 0 ? 'Sous budget' : 'Au-dessus du budget',
            icon: budgetVariance < 0 ? <TrendingDown size={20} /> : <TrendingUp size={20} />,
            accent: budgetVariance < 0 ? '#10b981' : '#ef4444',
            bg: budgetVariance < 0 ? '#ecfdf5' : '#fef2f2',
            border: budgetVariance < 0 ? '#bbf7d0' : '#fecaca',
            spark: [0.2,0.5,0.8,1.1,0.9,1.3,1.5,Math.abs(budgetVariance), Math.abs(budgetVariance)],
          },
        ].map((card, i) => (
          <div key={i} className="dash-card" style={{ background:'#fff', borderRadius:16, padding:'20px', border:`1px solid ${card.border}`, boxShadow:'0 1px 3px rgba(0,0,0,0.05)', animationDelay:`${i*0.05}s` }}>
            <div style={{ display:'flex', alignItems:'flex-start', justifyContent:'space-between', marginBottom:12 }}>
              <div style={{ width:40, height:40, borderRadius:11, background:card.bg, color:card.accent, display:'flex', alignItems:'center', justifyContent:'center' }}>
                {card.icon}
              </div>
              <Sparkline values={card.spark} color={card.accent} />
            </div>
            <div style={{ fontSize:26, fontWeight:800, color:card.accent, letterSpacing:'-0.02em', lineHeight:1 }}>{card.display}</div>
            <div style={{ fontSize:12, fontWeight:600, color:'#64748b', marginTop:4 }}>{card.label}</div>
            <div style={{ fontSize:11, color:'#94a3b8', marginTop:3 }}>{card.sub}</div>
          </div>
        ))}
      </div>

      {/* ── Middle row ── */}
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:14, animation:'fadeUp 0.5s 0.2s both' }}>

        {/* Project status donut-style */}
        <div className="dash-card" style={{ background:'#fff', borderRadius:16, padding:'22px', border:'1px solid #f1f5f9', boxShadow:'0 1px 3px rgba(0,0,0,0.05)' }}>
          <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:18 }}>
            <div style={{ width:32, height:32, borderRadius:9, background:'#eef2ff', display:'flex', alignItems:'center', justifyContent:'center' }}>
              <Activity size={16} color="#6366f1" />
            </div>
            <h2 style={{ fontSize:15, fontWeight:700, color:'#0f172a', margin:0 }}>État des Projets</h2>
          </div>
          <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
            {[
              { label:'En bonne voie', count:onTrackProjects,   color:'#10b981', bg:'#f0fdf4', bar: onTrackProjects / (stats?.total_projects||1) },
              { label:'En retard',     count:delayedProjects,   color:'#f59e0b', bg:'#fffbeb', bar: delayedProjects / (stats?.total_projects||1) },
              { label:'Terminés',      count:completedProjects, color:'#6366f1', bg:'#eef2ff', bar: completedProjects / (stats?.total_projects||1) },
              { label:'Critiques >30j',count:criticalProjects,  color:'#ef4444', bg:'#fef2f2', bar: criticalProjects / (stats?.total_projects||1) },
            ].map((item, i) => (
              <div key={i} style={{ background:item.bg, borderRadius:10, padding:'10px 14px' }}>
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:6 }}>
                  <span style={{ fontSize:13, fontWeight:600, color:item.color }}>{item.label}</span>
                  <span style={{ fontSize:20, fontWeight:800, color:item.color }}>{item.count}</span>
                </div>
                <div style={{ height:3, background:'rgba(0,0,0,0.06)', borderRadius:99, overflow:'hidden' }}>
                  <div style={{ height:'100%', width:`${Math.min(item.bar*100,100)}%`, background:item.color, borderRadius:99, transition:'width 1s ease' }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Top delayed */}
        <div className="dash-card" style={{ background:'#fff', borderRadius:16, padding:'22px', border:'1px solid #f1f5f9', boxShadow:'0 1px 3px rgba(0,0,0,0.05)' }}>
          <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:18 }}>
            <div style={{ display:'flex', alignItems:'center', gap:8 }}>
              <div style={{ width:32, height:32, borderRadius:9, background:'#fef2f2', display:'flex', alignItems:'center', justifyContent:'center' }}>
                <Zap size={16} color="#ef4444" />
              </div>
              <h2 style={{ fontSize:15, fontWeight:700, color:'#0f172a', margin:0 }}>Top Retards</h2>
            </div>
            <button className="nav-btn" onClick={() => navigate('/kpis')} style={{ background:'#f8fafc', border:'1px solid #e2e8f0', borderRadius:7, padding:'4px 10px', fontSize:11, fontWeight:600, color:'#64748b', cursor:'pointer', display:'flex', alignItems:'center', gap:4 }}>
              Voir tout <ArrowRight size={11} />
            </button>
          </div>
          {topDelayed.length === 0 ? (
            <div style={{ textAlign:'center', padding:'24px 0', color:'#94a3b8', fontSize:13 }}>
              <CheckCircle size={32} color="#22c55e" style={{ margin:'0 auto 8px', display:'block' }} />
              Aucun retard critique !
            </div>
          ) : (
            <div style={{ display:'flex', flexDirection:'column', gap:10 }}>
              {topDelayed.map((k, i) => {
                const proj = projects.find(p => p.project_id === k.project_id);
                const delay = k.schedule_variance_days || 0;
                const barW = Math.min((delay / 60) * 100, 100);
                const col = delay > 30 ? '#ef4444' : delay > 15 ? '#f59e0b' : '#f97316';
                return (
                  <div key={i} style={{ background:'#fafafa', borderRadius:10, padding:'11px 13px', border:'1px solid #f1f5f9' }}>
                    <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:7 }}>
                      <div>
                        <div style={{ fontSize:13, fontWeight:700, color:'#0f172a', lineHeight:1.3 }}>
                          {proj?.project_name || k.project_id}
                        </div>
                        <div style={{ display:'flex', alignItems:'center', gap:4, marginTop:3 }}>
                          {proj?.location && <><MapPin size={10} color="#94a3b8" /><span style={{ fontSize:10, color:'#94a3b8' }}>{proj.location}</span></>}
                        </div>
                      </div>
                      <div style={{ textAlign:'right', flexShrink:0 }}>
                        <div style={{ fontSize:16, fontWeight:800, color:col }}>{delay}j</div>
                        <RiskBadge level={k.risk_level} />
                      </div>
                    </div>
                    <div style={{ height:4, background:'#e2e8f0', borderRadius:99, overflow:'hidden' }}>
                      <div style={{ height:'100%', width:`${barW}%`, background:col, borderRadius:99, transition:'width 1s 0.3s ease' }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* ── Recent projects ── */}
      <div className="dash-card" style={{ background:'#fff', borderRadius:16, border:'1px solid #f1f5f9', boxShadow:'0 1px 3px rgba(0,0,0,0.05)', overflow:'hidden', animation:'fadeUp 0.5s 0.25s both' }}>
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'20px 24px', borderBottom:'1px solid #f8fafc' }}>
          <div style={{ display:'flex', alignItems:'center', gap:10 }}>
            <div style={{ width:32, height:32, borderRadius:9, background:'#eef2ff', display:'flex', alignItems:'center', justifyContent:'center' }}>
              <BarChart2 size={16} color="#6366f1" />
            </div>
            <h2 style={{ fontSize:15, fontWeight:700, color:'#0f172a', margin:0 }}>Projets Récents</h2>
          </div>
          <button className="nav-btn" onClick={() => navigate('/projects')} style={{ display:'flex', alignItems:'center', gap:5, background:'#f8fafc', border:'1px solid #e2e8f0', borderRadius:8, padding:'7px 14px', color:'#64748b', fontWeight:600, fontSize:13, cursor:'pointer' }}>
            Voir tous les projets <ArrowRight size={14} />
          </button>
        </div>

        <div style={{ padding:'0 8px 8px' }}>
          {/* Table header */}
          <div style={{ display:'grid', gridTemplateColumns:'2fr 1fr 1fr 2fr 80px', gap:16, padding:'10px 16px', borderBottom:'1px solid #f1f5f9' }}>
            {['Projet', 'Lieu', 'Client', 'Avancement', 'Statut'].map(h => (
              <div key={h} style={{ fontSize:11, fontWeight:700, color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.08em' }}>{h}</div>
            ))}
          </div>
          {projects.slice(0, 6).map((project, i) => {
            const pct = project.completion_percentage || 0;
            const col = pct >= 70 ? '#10b981' : pct >= 40 ? '#f59e0b' : '#ef4444';
            return (
              <div key={project.project_id} className="proj-row" style={{ display:'grid', gridTemplateColumns:'2fr 1fr 1fr 2fr 80px', gap:16, padding:'13px 16px', borderBottom: i < projects.length - 1 ? '1px solid #f8fafc' : 'none', alignItems:'center', background:'#fff', cursor:'pointer', borderRadius:8 }}
                onClick={() => navigate('/projects')}>
                <div>
                  <div style={{ fontWeight:700, fontSize:13, color:'#0f172a' }}>{project.project_name}</div>
                  <div style={{ fontSize:11, color:'#94a3b8', marginTop:1 }}>{project.project_id}</div>
                </div>
                <div style={{ display:'flex', alignItems:'center', gap:4, fontSize:12, color:'#64748b' }}>
                  <MapPin size={11} color="#94a3b8" />{project.location}
                </div>
                <div style={{ fontSize:12, color:'#64748b', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{project.client_name}</div>
                <div style={{ display:'flex', alignItems:'center', gap:10 }}>
                  <div style={{ flex:1, height:6, background:'#f1f5f9', borderRadius:99, overflow:'hidden' }}>
                    <div style={{ height:'100%', width:`${pct}%`, background:col, borderRadius:99, transition:'width 0.8s ease' }} />
                  </div>
                  <span style={{ fontSize:12, fontWeight:700, color:col, minWidth:30 }}>{pct}%</span>
                </div>
                <StatusPill status={project.status} />
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;