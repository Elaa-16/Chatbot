import React, { useState, useEffect } from 'react';
import { Bell, CheckCheck, AlertCircle, Info, CheckCircle, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

// ── Priority config ───────────────────────────────────────────────────────────
const PRIORITY = {
  Urgent: { bg:'#fef2f2', border:'#fecaca', strip:'#ef4444', dot:'#ef4444' },
  High:   { bg:'#fff7ed', border:'#fed7aa', strip:'#f97316', dot:'#f97316' },
  Medium: { bg:'#eff6ff', border:'#bfdbfe', strip:'#3b82f6', dot:'#3b82f6' },
  Low:    { bg:'#f8fafc', border:'#e2e8f0', strip:'#94a3b8', dot:'#cbd5e1' },
};

// ── Type config ───────────────────────────────────────────────────────────────
const TYPE = {
  Task:   { icon:<CheckCircle size={16}/>,  color:'#3b82f6',  bg:'#eff6ff'  },
  Alert:  { icon:<AlertCircle size={16}/>,  color:'#f97316',  bg:'#fff7ed'  },
  System: { icon:<Info size={16}/>,         color:'#64748b',  bg:'#f8fafc'  },
  Leave:  { icon:<Bell size={16}/>,         color:'#16a34a',  bg:'#f0fdf4'  },
  Leave_request: { icon:<Bell size={16}/>,  color:'#16a34a',  bg:'#f0fdf4'  },
};
const getType = t => TYPE[t] || { icon:<Bell size={16}/>, color:'#6366f1', bg:'#eef2ff' };

// ── Time format ───────────────────────────────────────────────────────────────
const timeAgo = d => {
  if (!d) return '—';
  const diff = Date.now() - new Date(d);
  const m = Math.floor(diff/60000), h = Math.floor(diff/3600000), days = Math.floor(diff/86400000);
  if (m < 1)  return 'À l\'instant';
  if (m < 60) return `Il y a ${m} min`;
  if (h < 24) return `Il y a ${h}h`;
  if (days < 7) return `Il y a ${days}j`;
  return new Date(d).toLocaleDateString('fr-FR', { day:'numeric', month:'short' });
};

// ── Main ──────────────────────────────────────────────────────────────────────
const Notifications = () => {
  const { user } = useAuth();
  const [notifs,  setNotifs]  = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);
  const [filter,  setFilter]  = useState('all');
  const [marking, setMarking] = useState(false);

  useEffect(() => {
    if (!user) return;
    load();
    const iv = setInterval(load, 30000);
    return () => clearInterval(iv);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter, user]);

  const load = async () => {
    try {
      setLoading(true);
      const ep = filter === 'unread' ? '/notifications/unread' : '/notifications';
      let data = (await api.get(ep)).data;
      if (filter === 'read') data = data.filter(n => n.is_read);
      setNotifs(data); setError(null);
    } catch(e) { setError(e.response?.data?.detail || 'Erreur chargement'); }
    finally { setLoading(false); }
  };

  const markOne = async id => {
    try { await api.put(`/notifications/${id}/read`); load(); }
    catch(e) { setError(e.response?.data?.detail || 'Erreur'); }
  };

  const markAll = async () => {
    setMarking(true);
    try { await api.put('/notifications/mark-all-read'); load(); }
    catch(e) { setError(e.response?.data?.detail || 'Erreur'); }
    finally { setMarking(false); }
  };

  const unread = notifs.filter(n => !n.is_read).length;

  const TABS = [
    { key:'all',    label:'Toutes',    count: notifs.length },
    { key:'unread', label:'Non lues',  count: unread },
    { key:'read',   label:'Lues',      count: notifs.length - unread },
  ];

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:20, fontFamily:"'Segoe UI',system-ui,sans-serif" }}>
      <style>{`
        @keyframes fadeUp{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
        .notif-card{transition:box-shadow .15s;}
        .notif-card:hover{box-shadow:0 4px 16px rgba(0,0,0,.08)!important;}
        .mark-btn{transition:all .15s;background:none;border:none;cursor:pointer;border-radius:7px;padding:6px;display:flex;align-items:center;}
        .mark-btn:hover{background:#eef2ff;}
        .tab-btn{transition:all .15s;border:none;cursor:pointer;font-weight:600;font-size:13px;padding:8px 16px;border-radius:8px;}
      `}</style>

      {/* Header */}
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', flexWrap:'wrap', gap:12, animation:'fadeUp .4s both' }}>
        <div style={{ display:'flex', alignItems:'center', gap:12 }}>
          <h1 style={{ fontSize:26, fontWeight:800, color:'#0f172a', margin:0, letterSpacing:'-0.02em' }}>Notifications</h1>
          {unread > 0 && (
            <span style={{ background:'#ef4444', color:'#fff', borderRadius:20, padding:'3px 11px', fontSize:12, fontWeight:800 }}>
              {unread} non lue{unread > 1 ? 's' : ''}
            </span>
          )}
        </div>
        {unread > 0 && (
          <button onClick={markAll} disabled={marking}
            style={{ display:'flex', alignItems:'center', gap:7, padding:'9px 18px', background:'linear-gradient(135deg,#4f46e5,#6366f1)', color:'#fff', border:'none', borderRadius:9, fontWeight:700, fontSize:14, cursor:marking?'not-allowed':'pointer', boxShadow:'0 4px 14px rgba(99,102,241,.35)', opacity:marking?.7:1 }}>
            <CheckCheck size={16} />
            {marking ? 'Marquage...' : 'Tout marquer comme lu'}
          </button>
        )}
      </div>

      {/* Error */}
      {error && (
        <div style={{ display:'flex', alignItems:'center', gap:12, background:'#fef2f2', border:'1px solid #fecaca', borderLeft:'4px solid #ef4444', borderRadius:12, padding:'12px 16px' }}>
          <span style={{ fontSize:13, color:'#dc2626', flex:1 }}>⚠️ {error}</span>
          <button onClick={()=>setError(null)} style={{ background:'none', border:'none', cursor:'pointer' }}><X size={15} color="#dc2626" /></button>
        </div>
      )}

      {/* Filter tabs */}
      <div style={{ display:'flex', gap:8, flexWrap:'wrap', animation:'fadeUp .4s .05s both' }}>
        {TABS.map(t => (
          <button key={t.key} className="tab-btn" onClick={()=>setFilter(t.key)}
            style={{ background: filter===t.key ? 'linear-gradient(135deg,#4f46e5,#6366f1)' : '#fff', color: filter===t.key?'#fff':'#64748b', boxShadow: filter===t.key?'0 4px 12px rgba(99,102,241,.25)':'none', border: filter===t.key?'none':'1px solid #e2e8f0' }}>
            {t.label}
            <span style={{ marginLeft:6, background: filter===t.key?'rgba(255,255,255,.25)':'#f1f5f9', color: filter===t.key?'#fff':'#64748b', borderRadius:20, padding:'1px 7px', fontSize:11, fontWeight:800 }}>
              {t.count}
            </span>
          </button>
        ))}
      </div>

      {/* Notifications list */}
      <div style={{ display:'flex', flexDirection:'column', gap:8, animation:'fadeUp .4s .1s both' }}>
        {loading && notifs.length === 0 && (
          <div style={{ textAlign:'center', padding:'40px 0', color:'#94a3b8', fontSize:14 }}>Chargement...</div>
        )}

        {!loading && notifs.length === 0 && (
          <div style={{ textAlign:'center', padding:'56px 0', background:'#fff', borderRadius:14, border:'1px solid #f1f5f9' }}>
            <Bell size={48} color="#e2e8f0" style={{ margin:'0 auto 12px', display:'block' }} />
            <p style={{ color:'#94a3b8', fontSize:15, fontWeight:600 }}>Aucune notification</p>
          </div>
        )}

        {notifs.map((n, i) => {
          const p  = PRIORITY[n.priority] || PRIORITY.Low;
          const t  = getType(n.type);
          const unread = !n.is_read;

          return (
            <div key={n.notification_id} className="notif-card"
              style={{ background: unread ? p.bg : '#fff', borderRadius:12, border:`1px solid ${unread ? p.border : '#f1f5f9'}`, overflow:'hidden', boxShadow:'0 1px 3px rgba(0,0,0,.05)', display:'flex', animation:`fadeUp .4s ${i*.03}s both` }}>

              {/* Priority strip */}
              <div style={{ width:4, background: unread ? p.strip : '#e2e8f0', flexShrink:0 }} />

              <div style={{ flex:1, padding:'14px 16px', display:'flex', alignItems:'flex-start', gap:12 }}>
                {/* Type icon */}
                <div style={{ width:36, height:36, borderRadius:10, background:t.bg, display:'flex', alignItems:'center', justifyContent:'center', color:t.color, flexShrink:0, marginTop:1 }}>
                  {t.icon}
                </div>

                {/* Content */}
                <div style={{ flex:1, minWidth:0 }}>
                  <div style={{ display:'flex', alignItems:'flex-start', justifyContent:'space-between', gap:12, marginBottom:4 }}>
                    <div>
                      <div style={{ fontWeight: unread ? 700 : 600, fontSize:14, color:'#0f172a', lineHeight:1.3 }}>
                        {n.title}
                        {unread && <span style={{ display:'inline-block', width:6, height:6, borderRadius:'50%', background:p.dot, marginLeft:7, verticalAlign:'middle' }} />}
                      </div>
                      <span style={{ fontSize:11, fontWeight:700, background:t.bg, color:t.color, borderRadius:20, padding:'2px 8px', display:'inline-block', marginTop:3 }}>
                        {n.type}
                      </span>
                    </div>
                    <span style={{ fontSize:11, color:'#94a3b8', whiteSpace:'nowrap', marginTop:2, fontWeight:500 }}>
                      {timeAgo(n.created_date)}
                    </span>
                  </div>

                  <p style={{ fontSize:13, color: unread ? '#374151' : '#64748b', margin:'6px 0 0', lineHeight:1.5 }}>
                    {n.message}
                  </p>

                  {n.link && (
                    <a href={n.link} style={{ display:'inline-block', marginTop:6, fontSize:12, fontWeight:600, color:'#6366f1', textDecoration:'none' }}>
                      Voir →
                    </a>
                  )}
                </div>

                {/* Mark as read */}
                {unread && (
                  <button className="mark-btn" onClick={()=>markOne(n.notification_id)} title="Marquer comme lu" style={{ flexShrink:0 }}>
                    <CheckCheck size={16} color="#6366f1" />
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Notifications;