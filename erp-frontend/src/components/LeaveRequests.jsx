import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { Calendar, Clock, CheckCircle, XCircle, AlertCircle, Plus, X, ChevronDown, Save} from 'lucide-react';
import api from '../services/api';

// ── Status config ─────────────────────────────────────────────────────────────
const STATUS_MAP = {
  Pending:   { bg:'#fffbeb', color:'#d97706', border:'#fde68a', icon:<Clock size={11}/>,        label:'En attente' },
  Approved:  { bg:'#f0fdf4', color:'#16a34a', border:'#bbf7d0', icon:<CheckCircle size={11}/>,  label:'Approuvé' },
  Rejected:  { bg:'#fef2f2', color:'#dc2626', border:'#fecaca', icon:<XCircle size={11}/>,      label:'Rejeté' },
  Cancelled: { bg:'#f8fafc', color:'#64748b', border:'#e2e8f0', icon:<AlertCircle size={11}/>,  label:'Annulé' },
};

const LEAVE_TYPE_MAP = {
  Annual:    { bg:'#eef2ff', color:'#4f46e5', label:'Annuel' },
  Sick:      { bg:'#fef2f2', color:'#dc2626', label:'Maladie' },
  Personal:  { bg:'#faf5ff', color:'#7c3aed', label:'Personnel' },
  Maternity: { bg:'#fdf2f8', color:'#db2777', label:'Maternité' },
  Emergency: { bg:'#fff7ed', color:'#ea580c', label:'Urgence' },
};

const StatusBadge = ({ status }) => {
  const s = STATUS_MAP[status] || STATUS_MAP.Pending;
  return (
    <span style={{ display:'inline-flex', alignItems:'center', gap:5, background:s.bg, color:s.color, border:`1px solid ${s.border}`, borderRadius:20, padding:'3px 10px', fontSize:11, fontWeight:700, whiteSpace:'nowrap' }}>
      {s.icon}{s.label}
    </span>
  );
};

const TypeBadge = ({ type }) => {
  const s = LEAVE_TYPE_MAP[type] || { bg:'#f8fafc', color:'#64748b', label: type };
  return (
    <span style={{ background:s.bg, color:s.color, borderRadius:20, padding:'3px 10px', fontSize:11, fontWeight:700, whiteSpace:'nowrap' }}>
      {s.label}
    </span>
  );
};

const inputStyle = {
  width:'100%', padding:'9px 12px', border:'1px solid #e2e8f0', borderRadius:8,
  fontSize:14, background:'#f8fafc', boxSizing:'border-box', outline:'none',
  fontFamily:'inherit', color:'#1e293b',
};

// ── Main ──────────────────────────────────────────────────────────────────────
const LeaveRequests = () => {
  const { user, isCEO, isManager, isRH } = useAuth();
  const canSubmit  = !isCEO && !isRH;
  const canReview  = isManager || isRH;

  const [requests,        setRequests]        = useState([]);
  const [pendingRequests, setPendingRequests] = useState([]);
  const [leaveStats,      setLeaveStats]      = useState(null);
  const [loading,         setLoading]         = useState(true);
  const [filter,          setFilter]          = useState('all');
  const [modal,           setModal]           = useState(null); // null | 'create' | { mode:'review', request, action }

  const [formData, setFormData] = useState({ leave_type:'Annual', start_date:'', end_date:'', reason:'' });
  const [reviewComment, setReviewComment] = useState('');
  const [saving, setSaving] = useState(false);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { loadData(); }, []);
  const loadData = async () => {
    try {
      const [rR, pR, sR] = await Promise.all([
        api.get('/leave-requests'),
        canReview ? api.get('/leave-requests/pending') : Promise.resolve({ data:[] }),
        api.get(`/employees/${user.employee_id}/leave-stats`),
      ]);
      setRequests(rR.data);
      setPendingRequests(pR.data);
      setLeaveStats(sR.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const calcDays = (s, e) => {
    if (!s || !e) return 0;
    return Math.ceil(Math.abs(new Date(e) - new Date(s)) / 86400000) + 1;
  };

  const handleSubmit = async () => {
    const totalDays = calcDays(formData.start_date, formData.end_date);
    if (totalDays <= 0) return alert('Date de fin invalide');
    setSaving(true);
    try {
      const empRes = await api.get(`/employees/${user.employee_id}`);
      const emp    = empRes.data;
      await api.post('/leave-requests', {
        request_id:    `LR${Date.now()}`,
        employee_id:   user.employee_id,
        employee_name: `${emp.first_name} ${emp.last_name}`,
        leave_type:    formData.leave_type,
        start_date:    formData.start_date,
        end_date:      formData.end_date,
        total_days:    totalDays,
        reason:        formData.reason,
      });
      setModal(null);
      setFormData({ leave_type:'Annual', start_date:'', end_date:'', reason:'' });
      loadData();
    } catch (e) { alert(e.response?.data?.detail || 'Erreur'); }
    finally { setSaving(false); }
  };

  const handleReview = async () => {
    const { request, action } = modal;
    if (action === 'reject' && !reviewComment.trim()) return alert('Raison du rejet requise');
    setSaving(true);
    try {
      if (action === 'approve') {
        await api.put(`/leave-requests/${request.request_id}/approve`, null, { params:{ review_comment: reviewComment } });
      } else {
        await api.put(`/leave-requests/${request.request_id}/reject?review_comment=${encodeURIComponent(reviewComment)}`);
      }
      setModal(null);
      setReviewComment('');
      loadData();
    } catch (e) { alert(e.response?.data?.detail || 'Erreur'); }
    finally { setSaving(false); }
  };

  const handleCancel = async (id) => {
    if (!window.confirm('Annuler cette demande ?')) return;
    try { await api.put(`/leave-requests/${id}/cancel`); loadData(); }
    catch (e) { alert(e.response?.data?.detail || 'Erreur'); }
  };

  const filtered = requests.filter(r =>
    filter === 'all' ? true : r.status === filter.charAt(0).toUpperCase() + filter.slice(1)
  );

  const FILTERS = [
    { key:'all',      label:'Toutes',      count: requests.length },
    { key:'pending',  label:'En attente',  count: requests.filter(r=>r.status==='Pending').length },
    { key:'approved', label:'Approuvées',  count: requests.filter(r=>r.status==='Approved').length },
    { key:'rejected', label:'Rejetées',    count: requests.filter(r=>r.status==='Rejected').length },
  ];

  if (loading) return (
    <div style={{ display:'flex', alignItems:'center', justifyContent:'center', height:300, gap:12 }}>
      <div style={{ width:36, height:36, border:'3px solid #e2e8f0', borderTop:'3px solid #6366f1', borderRadius:'50%', animation:'spin .8s linear infinite' }} />
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );

  const days = calcDays(formData.start_date, formData.end_date);

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:20, fontFamily:"'Segoe UI',system-ui,sans-serif" }}>
      <style>{`
        @keyframes spin{to{transform:rotate(360deg)}}
        @keyframes fadeUp{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
        .leave-card{transition:box-shadow .18s;}
        .leave-card:hover{box-shadow:0 6px 20px rgba(0,0,0,.08)!important;}
        .filter-btn{transition:all .15s;border:none;cursor:pointer;font-weight:600;font-size:13px;border-radius:8px;padding:8px 16px;}
        .action-btn{transition:all .15s;border:none;cursor:pointer;font-weight:600;font-size:12px;border-radius:8px;padding:7px 14px;display:flex;align-items:center;gap:5px;}
        .action-btn:hover{opacity:.85;}
      `}</style>

      {/* ── Header ── */}
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', flexWrap:'wrap', gap:12, animation:'fadeUp .4s both' }}>
        <div>
          <h1 style={{ fontSize:26, fontWeight:800, color:'#0f172a', margin:0, letterSpacing:'-0.02em' }}>Congés</h1>
          <p style={{ color:'#64748b', fontSize:14, margin:'4px 0 0' }}>Demandes et suivi des absences</p>
        </div>
        {canSubmit && (
          <button onClick={() => setModal('create')} style={{ display:'flex', alignItems:'center', gap:7, padding:'9px 18px', background:'linear-gradient(135deg,#4f46e5,#6366f1)', color:'#fff', border:'none', borderRadius:9, fontWeight:700, fontSize:14, cursor:'pointer', boxShadow:'0 4px 14px rgba(99,102,241,.35)' }}>
            <Plus size={16} /> Nouvelle demande
          </button>
        )}
      </div>

      {/* ── Stats cards — hidden for RH ── */}
      {!isRH && !isCEO && leaveStats && (

        <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(140px,1fr))', gap:12, animation:'fadeUp .4s .05s both' }}>
          {[
            { label:'Droit annuel',  value: leaveStats.annual_leave_total||0,     color:'#6366f1', bg:'#eef2ff', border:'#c7d2fe' },
            { label:'Jours pris',    value: leaveStats.annual_leave_taken||0,     color:'#f59e0b', bg:'#fffbeb', border:'#fde68a' },
            { label:'Restants',      value: leaveStats.annual_leave_remaining||0, color:'#16a34a', bg:'#f0fdf4', border:'#bbf7d0' },
            { label:'Maladie',       value: leaveStats.sick_leave_taken||0,       color:'#dc2626', bg:'#fef2f2', border:'#fecaca' },
            { label:'Autres',        value: leaveStats.other_leave_taken||0,      color:'#7c3aed', bg:'#faf5ff', border:'#ddd6fe' },
          ].map((s, i) => (
            <div key={i} style={{ background:s.bg, border:`1px solid ${s.border}`, borderRadius:12, padding:'14px 16px', textAlign:'center' }}>
              <div style={{ fontSize:26, fontWeight:800, color:s.color, lineHeight:1 }}>{s.value}</div>
              <div style={{ fontSize:11, fontWeight:600, color:'#64748b', marginTop:4 }}>{s.label}</div>
            </div>
          ))}
          {/* Annual leave progress bar */}
          <div style={{ background:'#fff', border:'1px solid #e2e8f0', borderRadius:12, padding:'14px 16px', gridColumn:'1 / -1' }}>
            <div style={{ display:'flex', justifyContent:'space-between', marginBottom:8 }}>
              <span style={{ fontSize:12, fontWeight:700, color:'#64748b' }}>Utilisation congés annuels</span>
              <span style={{ fontSize:12, fontWeight:700, color:'#6366f1' }}>
                {leaveStats.annual_leave_taken||0} / {leaveStats.annual_leave_total||35} j
              </span>
            </div>
            <div style={{ height:6, background:'#f1f5f9', borderRadius:99, overflow:'hidden' }}>
              <div style={{ height:'100%', width:`${Math.min(((leaveStats.annual_leave_taken||0)/(leaveStats.annual_leave_total||35))*100,100)}%`, background:'linear-gradient(90deg,#6366f1,#818cf8)', borderRadius:99, transition:'width .6s ease' }} />
            </div>
          </div>
        </div>
      )}

      {/* ── Pending alert — for RH and managers ── */}
      {canReview && pendingRequests.length > 0 && (
        <div style={{ display:'flex', alignItems:'center', gap:12, background:'#fffbeb', border:'1px solid #fde68a', borderLeft:'4px solid #f59e0b', borderRadius:12, padding:'14px 18px', animation:'fadeUp .4s .1s both' }}>
          <AlertCircle size={18} color="#d97706" style={{ flexShrink:0 }} />
          <div>
            <strong style={{ fontSize:14, color:'#92400e' }}>
              {pendingRequests.length} demande{pendingRequests.length>1?'s':''} en attente d'approbation
            </strong>
            <p style={{ fontSize:13, color:'#b45309', margin:'2px 0 0' }}>Consultez la liste ci-dessous pour traiter les demandes.</p>
          </div>
        </div>
      )}

      {/* ── Filter tabs ── */}
      <div style={{ display:'flex', gap:8, flexWrap:'wrap', animation:'fadeUp .4s .12s both' }}>
        {FILTERS.map(f => (
          <button key={f.key} className="filter-btn" onClick={() => setFilter(f.key)}
            style={{ background: filter===f.key ? 'linear-gradient(135deg,#4f46e5,#6366f1)' : '#fff', color: filter===f.key ? '#fff' : '#64748b', boxShadow: filter===f.key ? '0 4px 12px rgba(99,102,241,.25)' : 'none', border: filter===f.key ? 'none' : '1px solid #e2e8f0' }}>
            {f.label}
            {f.count > 0 && (
              <span style={{ marginLeft:6, background: filter===f.key ? 'rgba(255,255,255,0.25)' : '#f1f5f9', color: filter===f.key ? '#fff' : '#64748b', borderRadius:20, padding:'1px 7px', fontSize:11, fontWeight:700 }}>
                {f.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ── Request cards ── */}
      <div style={{ display:'flex', flexDirection:'column', gap:10, animation:'fadeUp .4s .15s both' }}>
        {filtered.map((req, i) => (
          <div key={req.request_id} className="leave-card" style={{ background:'#fff', borderRadius:14, border:'1px solid #f1f5f9', padding:'18px 20px', boxShadow:'0 1px 3px rgba(0,0,0,.05)' }}>
            <div style={{ display:'flex', alignItems:'flex-start', justifyContent:'space-between', gap:12, flexWrap:'wrap' }}>

              {/* Left */}
              <div style={{ flex:1, minWidth:0 }}>
                <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:8, flexWrap:'wrap' }}>
                  {/* Avatar */}
                  <div style={{ width:36, height:36, borderRadius:'50%', background:'linear-gradient(135deg,#e0e7ff,#c7d2fe)', display:'flex', alignItems:'center', justifyContent:'center', fontSize:13, fontWeight:700, color:'#4f46e5', flexShrink:0 }}>
                    {(req.employee_name||'?').split(' ').map(w=>w[0]).slice(0,2).join('')}
                  </div>
                  <div>
                    <div style={{ fontWeight:700, fontSize:14, color:'#0f172a' }}>{req.employee_name}</div>
                    <div style={{ fontSize:11, color:'#94a3b8' }}>{req.request_id}</div>
                  </div>
                  <TypeBadge type={req.leave_type} />
                  <StatusBadge status={req.status} />
                </div>

                <div style={{ display:'flex', alignItems:'center', gap:16, flexWrap:'wrap' }}>
                  <div style={{ display:'flex', alignItems:'center', gap:5, fontSize:13, color:'#64748b' }}>
                    <Calendar size={13} color="#94a3b8" />
                    <span>{req.start_date}</span>
                    <span style={{ color:'#cbd5e1' }}>→</span>
                    <span>{req.end_date}</span>
                  </div>
                  <div style={{ background:'#eef2ff', color:'#4f46e5', borderRadius:20, padding:'2px 10px', fontSize:12, fontWeight:700 }}>
                    {req.total_days} jour{req.total_days>1?'s':''}
                  </div>
                </div>

                {req.reason && (
                  <div style={{ marginTop:8, fontSize:13, color:'#64748b', background:'#f8fafc', borderRadius:8, padding:'7px 10px' }}>
                    💬 {req.reason}
                  </div>
                )}
                {req.review_comment && (
                  <div style={{ marginTop:6, fontSize:13, color:'#64748b', background:'#f0fdf4', borderRadius:8, padding:'7px 10px', borderLeft:'3px solid #16a34a' }}>
                    📝 {req.review_comment}
                  </div>
                )}
              </div>

              {/* Actions */}
              {req.status === 'Pending' && (
                <div style={{ display:'flex', gap:8, flexShrink:0 }}>
                  {canReview && (isRH || (isManager && user.supervised_employees?.includes(req.employee_id))) && (
                    <>
                      <button className="action-btn" onClick={() => { setModal({ mode:'review', request:req, action:'approve' }); setReviewComment(''); }}
                        style={{ background:'#f0fdf4', color:'#16a34a' }}>
                        <CheckCircle size={13} /> Approuver
                      </button>
                      <button className="action-btn" onClick={() => { setModal({ mode:'review', request:req, action:'reject' }); setReviewComment(''); }}
                        style={{ background:'#fef2f2', color:'#dc2626' }}>
                        <XCircle size={13} /> Rejeter
                      </button>
                    </>
                  )}
                  {req.employee_id === user.employee_id && (
                    <button className="action-btn" onClick={() => handleCancel(req.request_id)}
                      style={{ background:'#f8fafc', color:'#64748b', border:'1px solid #e2e8f0' }}>
                      <X size={13} /> Annuler
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {filtered.length === 0 && (
          <div style={{ textAlign:'center', padding:'48px 0', background:'#fff', borderRadius:14, border:'1px solid #f1f5f9' }}>
            <Calendar size={48} color="#e2e8f0" style={{ margin:'0 auto 12px', display:'block' }} />
            <p style={{ color:'#94a3b8', fontSize:15, fontWeight:600 }}>Aucune demande trouvée</p>
          </div>
        )}
      </div>

      {/* ── Create Modal ── */}
      {modal === 'create' && (
        <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.5)', zIndex:1000, display:'flex', alignItems:'center', justifyContent:'center', padding:20, backdropFilter:'blur(4px)' }}>
          <div style={{ background:'#fff', borderRadius:18, width:'100%', maxWidth:460, boxShadow:'0 32px 80px rgba(0,0,0,.2)', overflow:'hidden' }}>
            <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'20px 24px', borderBottom:'1px solid #f1f5f9' }}>
              <div>
                <h2 style={{ fontSize:17, fontWeight:800, color:'#0f172a', margin:0 }}>📅 Nouvelle demande de congé</h2>
                <p style={{ fontSize:13, color:'#64748b', margin:'3px 0 0' }}>Remplissez les informations ci-dessous</p>
              </div>
              <button onClick={() => setModal(null)} style={{ width:32, height:32, borderRadius:8, border:'1px solid #e2e8f0', background:'#f8fafc', cursor:'pointer', display:'flex', alignItems:'center', justifyContent:'center' }}>
                <X size={15} color="#64748b" />
              </button>
            </div>

            <div style={{ padding:'20px 24px', display:'flex', flexDirection:'column', gap:14 }}>
              {/* Type */}
              <div>
                <label style={{ display:'block', fontSize:11, fontWeight:700, color:'#64748b', textTransform:'uppercase', letterSpacing:'0.07em', marginBottom:5 }}>Type de congé *</label>
                <div style={{ position:'relative' }}>
                  <select value={formData.leave_type} onChange={e=>setFormData(f=>({...f,leave_type:e.target.value}))}
                    style={{ ...inputStyle, paddingRight:30, appearance:'none', cursor:'pointer' }}>
                    <option value="Annual">Congé Annuel</option>
                    <option value="Sick">Congé Maladie</option>
                    <option value="Personal">Congé Personnel</option>
                    <option value="Emergency">Urgence</option>
                  </select>
                  <ChevronDown size={13} style={{ position:'absolute', right:10, top:'50%', transform:'translateY(-50%)', color:'#94a3b8', pointerEvents:'none' }} />
                </div>
              </div>

              {/* Dates */}
              <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:12 }}>
                <div>
                  <label style={{ display:'block', fontSize:11, fontWeight:700, color:'#64748b', textTransform:'uppercase', letterSpacing:'0.07em', marginBottom:5 }}>Date de début *</label>
                  <input type="date" value={formData.start_date} onChange={e=>setFormData(f=>({...f,start_date:e.target.value}))} style={inputStyle} required />
                </div>
                <div>
                  <label style={{ display:'block', fontSize:11, fontWeight:700, color:'#64748b', textTransform:'uppercase', letterSpacing:'0.07em', marginBottom:5 }}>Date de fin *</label>
                  <input type="date" value={formData.end_date} onChange={e=>setFormData(f=>({...f,end_date:e.target.value}))} style={inputStyle} required />
                </div>
              </div>

              {/* Duration preview */}
              {days > 0 && (
                <div style={{ background:'#eef2ff', border:'1px solid #c7d2fe', borderRadius:10, padding:'12px 14px' }}>
                  <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                    <span style={{ fontSize:13, fontWeight:700, color:'#4f46e5' }}>📊 Durée : {days} jour{days>1?'s':''}</span>
                    {formData.leave_type === 'Annual' && leaveStats && (
                      <span style={{ fontSize:12, color:'#6366f1' }}>
                        Restant après : <strong>{leaveStats.annual_leave_remaining - days}j</strong>
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* Reason */}
              <div>
                <label style={{ display:'block', fontSize:11, fontWeight:700, color:'#64748b', textTransform:'uppercase', letterSpacing:'0.07em', marginBottom:5 }}>Raison (optionnel)</label>
                <textarea value={formData.reason} onChange={e=>setFormData(f=>({...f,reason:e.target.value}))}
                  rows={3} placeholder="Décrivez la raison de votre demande..." style={{ ...inputStyle, resize:'vertical' }} />
              </div>
            </div>

            <div style={{ padding:'16px 24px', borderTop:'1px solid #f1f5f9', display:'flex', gap:10 }}>
              <button onClick={() => setModal(null)} style={{ padding:'10px 20px', borderRadius:8, border:'1px solid #e2e8f0', background:'#fff', color:'#64748b', fontWeight:600, fontSize:14, cursor:'pointer' }}>
                Annuler
              </button>
              <button onClick={handleSubmit} disabled={saving} style={{ flex:1, padding:'10px', borderRadius:8, border:'none', background:'linear-gradient(135deg,#4f46e5,#6366f1)', color:'#fff', fontWeight:700, fontSize:14, cursor:saving?'not-allowed':'pointer', display:'flex', alignItems:'center', justifyContent:'center', gap:6, opacity:saving?.7:1 }}>
                <Save size={14} />
                {saving ? 'Envoi...' : 'Soumettre la demande'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Review Modal ── */}
      {modal?.mode === 'review' && (
        <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.5)', zIndex:1000, display:'flex', alignItems:'center', justifyContent:'center', padding:20, backdropFilter:'blur(4px)' }}>
          <div style={{ background:'#fff', borderRadius:18, width:'100%', maxWidth:440, boxShadow:'0 32px 80px rgba(0,0,0,.2)', overflow:'hidden' }}>
            <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'20px 24px', borderBottom:'1px solid #f1f5f9' }}>
              <h2 style={{ fontSize:17, fontWeight:800, color:'#0f172a', margin:0 }}>
                {modal.action === 'approve' ? '✅ Approuver la demande' : '❌ Rejeter la demande'}
              </h2>
              <button onClick={() => setModal(null)} style={{ width:32, height:32, borderRadius:8, border:'1px solid #e2e8f0', background:'#f8fafc', cursor:'pointer', display:'flex', alignItems:'center', justifyContent:'center' }}>
                <X size={15} color="#64748b" />
              </button>
            </div>

            <div style={{ padding:'20px 24px', display:'flex', flexDirection:'column', gap:14 }}>
              {/* Request summary */}
              <div style={{ background:'#f8fafc', borderRadius:10, padding:'14px 16px', display:'flex', flexDirection:'column', gap:7 }}>
                {[
                  { label:'Employé',  value: modal.request.employee_name },
                  { label:'Type',     value: modal.request.leave_type },
                  { label:'Période',  value: `${modal.request.start_date} → ${modal.request.end_date}` },
                  { label:'Durée',    value: `${modal.request.total_days} jour${modal.request.total_days>1?'s':''}` },
                ].map((r,i) => (
                  <div key={i} style={{ display:'flex', justifyContent:'space-between', fontSize:13 }}>
                    <span style={{ color:'#94a3b8', fontWeight:600 }}>{r.label}</span>
                    <span style={{ color:'#0f172a', fontWeight:700 }}>{r.value}</span>
                  </div>
                ))}
              </div>

              {/* Comment */}
              <div>
                <label style={{ display:'block', fontSize:11, fontWeight:700, color:'#64748b', textTransform:'uppercase', letterSpacing:'0.07em', marginBottom:5 }}>
                  Commentaire {modal.action === 'reject' && <span style={{ color:'#ef4444' }}>*</span>}
                </label>
                <textarea value={reviewComment} onChange={e=>setReviewComment(e.target.value)}
                  rows={3} placeholder={modal.action === 'approve' ? 'Optionnel...' : 'Raison du rejet (requis)'}
                  style={{ ...inputStyle, resize:'vertical' }} />
              </div>
            </div>

            <div style={{ padding:'16px 24px', borderTop:'1px solid #f1f5f9', display:'flex', gap:10 }}>
              <button onClick={() => setModal(null)} style={{ padding:'10px 20px', borderRadius:8, border:'1px solid #e2e8f0', background:'#fff', color:'#64748b', fontWeight:600, fontSize:14, cursor:'pointer' }}>
                Annuler
              </button>
              <button onClick={handleReview} disabled={saving}
                style={{ flex:1, padding:'10px', borderRadius:8, border:'none', background: modal.action==='approve' ? 'linear-gradient(135deg,#16a34a,#22c55e)' : 'linear-gradient(135deg,#dc2626,#ef4444)', color:'#fff', fontWeight:700, fontSize:14, cursor:saving?'not-allowed':'pointer', opacity:saving?.7:1 }}>
                {saving ? 'Traitement...' : modal.action === 'approve' ? 'Confirmer l\'approbation' : 'Confirmer le rejet'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LeaveRequests;