import React, { useState, useEffect } from 'react';
import { getWhitelist, createWhitelist, updateWhitelist, deleteWhitelist } from '../services/api';
import { Shield, Plus, Pencil, Trash2, Search, X, Save, AlertCircle } from 'lucide-react';

const ApiWhitelist = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [modal, setModal] = useState(null); // null | { mode: 'create'|'edit', item? }
  const [error, setError] = useState('');

  useEffect(() => { loadItems(); }, []);

  const loadItems = async () => {
    try {
      setLoading(true);
      const res = await getWhitelist();
      setItems(res.data);
    } catch (e) {
      console.error(e);
      setError('Erreur lors du chargement de la liste blanche.');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Voulez-vous vraiment supprimer cet endpoint de la liste blanche ?')) return;
    try {
      await deleteWhitelist(id);
      loadItems();
    } catch (e) {
      alert(e.response?.data?.detail || 'Erreur lors de la suppression');
    }
  };

  const filtered = items.filter(i => 
  (i.endpoint || '').toLowerCase().includes(search.toLowerCase()) || 
  (i.description || '').toLowerCase().includes(search.toLowerCase())
);

  return (
    <div style={{ padding: '0 0 40px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 800, color: '#1e293b', margin: 0, display: 'flex', alignItems: 'center', gap: 10 }}>
            <Shield size={28} color="#4f46e5" />
            Liste Blanche API
          </h1>
          <p style={{ color: '#64748b', margin: '4px 0 0', fontSize: 14 }}>
            Gérez les endpoints autorisés pour les intégrations sans authentification complète.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <div style={{ position: 'relative' }}>
            <Search size={15} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Rechercher..."
              style={{ padding: '9px 12px 9px 32px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 14, width: 220, background: '#f8fafc' }}
            />
          </div>
          <button
            onClick={() => setModal({ mode: 'create' })}
            style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '9px 18px', background: 'linear-gradient(135deg, #4f46e5, #6366f1)', color: '#fff', border: 'none', borderRadius: 8, fontWeight: 600, fontSize: 14, cursor: 'pointer', boxShadow: '0 4px 14px rgba(99,102,241,0.35)', whiteSpace: 'nowrap' }}
          >
            <Plus size={16} /> Ajouter
          </button>
        </div>
      </div>

      {error && (
         <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, padding: '14px', marginBottom: 20, color: '#dc2626', fontSize: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
            <AlertCircle size={18} /> {error}
         </div>
      )}

      <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #e2e8f0', overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.06)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
              <th style={{ padding: '14px 20px', fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Endpoint</th>
              <th style={{ padding: '14px 20px', fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Description</th>
              <th style={{ padding: '14px 20px', fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Statut</th>
              <th style={{ padding: '14px 20px', fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={4} style={{ padding: 30, textAlign: 'center', color: '#94a3b8' }}>Chargement...</td></tr>
            ) : filtered.length === 0 ? (
              <tr><td colSpan={4} style={{ padding: 30, textAlign: 'center', color: '#94a3b8' }}>Aucun endpoint trouvé.</td></tr>
            ) : (
              filtered.map(item => (
                <tr key={item.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                  <td style={{ padding: '14px 20px', fontSize: 14, fontWeight: 600, color: '#0f172a' }}>
                    <code style={{ background: '#f1f5f9', padding: '2px 6px', borderRadius: 4, color: '#4f46e5' }}>{item.endpoint}</code>
                  </td>
                  <td style={{ padding: '14px 20px', fontSize: 14, color: '#475569' }}>{item.description}</td>
                  <td style={{ padding: '14px 20px' }}>
                    <span style={{ 
                      padding: '4px 10px', 
                      borderRadius: 20, 
                      fontSize: 11, 
                      fontWeight: 700, 
                      background: item.is_active ? '#dcfce7' : '#f1f5f9',
                      color: item.is_active ? '#15803d' : '#64748b'
                    }}>
                      {item.is_active ? 'Actif' : 'Inactif'}
                    </span>
                  </td>
                  <td style={{ padding: '14px 20px', textAlign: 'right' }}>
                    <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                      <button
                        onClick={() => setModal({ mode: 'edit', item })}
                        style={{ width: 32, height: 32, borderRadius: 8, border: '1px solid #e2e8f0', background: '#f8fafc', color: '#4f46e5', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                      >
                        <Pencil size={14} />
                      </button>
                      <button
                        onClick={() => handleDelete(item.id)}
                        style={{ width: 32, height: 32, borderRadius: 8, border: '1px solid #fecaca', background: '#fef2f2', color: '#ef4444', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {modal && <WhitelistModal mode={modal.mode} item={modal.item} onClose={() => setModal(null)} onSave={() => { setModal(null); loadItems(); }} />}
    </div>
  );
};

const WhitelistModal = ({ mode, item, onClose, onSave }) => {
  const isCreate = mode === 'create';
  const [form, setForm] = useState(
  isCreate 
    ? { endpoint: '', methods: 'GET', description: '', is_active: true } 
    : { ...item }
);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    if (!form.endpoint.trim()) 
      return setError('Le chemin (endpoint) est requis.');
    setError('');
    setSaving(true);
    try {
      if (isCreate) {
        await createWhitelist(form);
      } else {
        await updateWhitelist(item.id, form);
      }
      onSave();
    } catch (e) {
      setError(e.response?.data?.detail || 'Erreur lors de la sauvegarde.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}>
      <div style={{ background: '#fff', borderRadius: 16, width: '100%', maxWidth: 480, overflow: 'hidden', display: 'flex', flexDirection: 'column', boxShadow: '0 25px 60px rgba(0,0,0,0.2)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 24px', borderBottom: '1px solid #f1f5f9' }}>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1e293b', margin: 0 }}>
              {isCreate ? 'Nouvel Endpoint' : 'Modifier cet Endpoint'}
            </h2>
          </div>
          <button onClick={onClose} style={{ background: '#f1f5f9', border: 'none', borderRadius: 8, padding: 8, cursor: 'pointer', display: 'flex' }}>
            <X size={18} color="#64748b" />
          </button>
        </div>

        <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 16 }}>
          {error && <div style={{ color: '#ef4444', fontSize: 13, background: '#fef2f2', padding: 10, borderRadius: 8 }}>{error}</div>}
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ fontSize: 13, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Chemin (Endpoint)</label>
            <input
              value={form.endpoint}
              onChange={e => setForm({ ...form, endpoint: e.target.value })}
              placeholder="/api/example"
              style={{ width: '100%', padding: '10px 14px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 14, boxSizing: 'border-box' }}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ fontSize: 13, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Description</label>
            <input
              value={form.description || ''}
              onChange={e => setForm({ ...form, description: e.target.value })}
              placeholder="Description de l'usage"
              style={{ width: '100%', padding: '10px 14px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 14, boxSizing: 'border-box' }}
            />
          </div>

          <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', marginTop: 8 }}>
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={e => setForm({ ...form, is_active: e.target.checked })}
              style={{ width: 18, height: 18, cursor: 'pointer' }}
            />
            <span style={{ fontSize: 14, fontWeight: 600, color: '#334155' }}>Endpoint Actif</span>
          </label>
        </div>

        <div style={{ padding: '16px 24px', borderTop: '1px solid #f1f5f9', display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
          <button onClick={onClose} style={{ padding: '9px 20px', borderRadius: 8, border: '1px solid #e2e8f0', background: '#fff', color: '#64748b', fontWeight: 600, fontSize: 14, cursor: 'pointer' }}>Annuler</button>
          <button onClick={handleSubmit} disabled={saving} style={{ padding: '9px 20px', borderRadius: 8, border: 'none', background: 'linear-gradient(135deg, #4f46e5, #6366f1)', color: '#fff', fontWeight: 600, fontSize: 14, cursor: saving ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
            <Save size={15} /> {saving ? '...' : 'Sauvegarder'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ApiWhitelist;
