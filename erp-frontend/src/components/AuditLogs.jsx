import React, { useState, useEffect } from 'react';
import { getActivityLogs } from '../services/api';
import { FileBarChart, Search, ArrowDownToLine } from 'lucide-react';

const AuditLogs = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [params, setParams] = useState({ limit: 100, action_type: '', entity_type: '' });
  const [search, setSearch] = useState('');

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { loadLogs(); }, [params]);

  const loadLogs = async () => {
    try {
      setLoading(true);
      const res = await getActivityLogs(params);
      setLogs(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const filteredLogs = logs.filter(log => 
    log.user_id.toLowerCase().includes(search.toLowerCase()) ||
    (log.details && log.details.toLowerCase().includes(search.toLowerCase())) || 
    log.entity_id.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div style={{ padding: '0 0 40px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 800, color: '#1e293b', margin: 0, display: 'flex', alignItems: 'center', gap: 10 }}>
            <FileBarChart size={28} color="#e11d48" />
            Journaux d'Audit
          </h1>
          <p style={{ color: '#64748b', margin: '4px 0 0', fontSize: 14 }}>
            Consultez l'historique de toutes les opérations importantes réalisées sur le système.
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 14, marginBottom: 20, flexWrap: 'wrap', alignItems: 'center', background: '#fff', padding: 16, borderRadius: 12, border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.06)' }}>
        <div style={{ position: 'relative', flex: '1 1 200px' }}>
          <Search size={15} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Rechercher (Utilisateur, Entité, Détails)..."
            style={{ width: '100%', padding: '9px 12px 9px 34px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 14, boxSizing: 'border-box' }}
          />
        </div>

        <select 
          value={params.action_type || ''} 
          onChange={e => setParams({ ...params, action_type: e.target.value })}
          style={{ padding: '9px 12px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 14, minWidth: 150 }}
        >
          <option value="">Toutes les actions</option>
          <option value="create">Création (create)</option>
          <option value="update">Mise à jour (update)</option>
          <option value="delete">Suppression (delete)</option>
          <option value="login">Connexion (login)</option>
        </select>

        <select 
          value={params.entity_type || ''} 
          onChange={e => setParams({ ...params, entity_type: e.target.value })}
          style={{ padding: '9px 12px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 14, minWidth: 150 }}
        >
          <option value="">Toutes les entités</option>
          <option value="user">Utilisateur</option>
          <option value="project">Projet</option>
          <option value="task">Tâche</option>
          <option value="whitelist">Whitelist</option>
        </select>
        
        <button
          onClick={() => {
            alert('Export CSV - À implémenter si désiré');
          }}
          style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '9px 16px', background: '#f1f5f9', color: '#334155', border: '1px solid #e2e8f0', borderRadius: 8, fontWeight: 600, fontSize: 14, cursor: 'pointer' }}
        >
          <ArrowDownToLine size={16} /> Export
        </button>
      </div>

      <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #e2e8f0', overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.06)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
              <th style={{ padding: '14px 20px', fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Date & Heure</th>
              <th style={{ padding: '14px 20px', fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Utilisateur</th>
              <th style={{ padding: '14px 20px', fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Action</th>
              <th style={{ padding: '14px 20px', fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Entité (ID)</th>
              <th style={{ padding: '14px 20px', fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Détails</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} style={{ padding: 30, textAlign: 'center', color: '#94a3b8' }}>Chargement...</td></tr>
            ) : filteredLogs.length === 0 ? (
              <tr><td colSpan={5} style={{ padding: 30, textAlign: 'center', color: '#94a3b8' }}>Aucun journal trouvé.</td></tr>
            ) : (
              filteredLogs.map(log => {
                const actionColors = {
                  create: { bg: '#dcfce7', text: '#15803d' },
                  update: { bg: '#e0e7ff', text: '#4338ca' },
                  delete: { bg: '#fee2e2', text: '#b91c1c' },
                  login:  { bg: '#fef3c7', text: '#b45309' },
                };
                const style = actionColors[log.action_type] || { bg: '#f1f5f9', text: '#475569' };

                return (
                  <tr key={log.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={{ padding: '14px 20px', fontSize: 13, color: '#64748b' }}>
                      {new Date(log.timestamp).toLocaleString('fr-FR')}
                    </td>
                    <td style={{ padding: '14px 20px', fontSize: 14, fontWeight: 600, color: '#0f172a' }}>
                      <code style={{ background: '#f1f5f9', padding: '2px 6px', borderRadius: 4, color: '#334155' }}>
                        {log.user_id}
                      </code>
                    </td>
                    <td style={{ padding: '14px 20px' }}>
                      <span style={{ 
                        padding: '4px 10px', borderRadius: 20, fontSize: 11, fontWeight: 700, 
                        background: style.bg, color: style.text, textTransform: 'capitalize'
                      }}>
                        {log.action_type}
                      </span>
                    </td>
                    <td style={{ padding: '14px 20px', fontSize: 13, color: '#475569' }}>
                      <span style={{ fontWeight: 600 }}>{log.entity_type}</span>
                      <br />
                      <span style={{ fontSize: 11, color: '#94a3b8' }}>{log.entity_id}</span>
                    </td>
                    <td style={{ padding: '14px 20px', fontSize: 13, color: '#475569', maxWidth: 300, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={log.details}>
                      {log.details || '-'}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default AuditLogs;
