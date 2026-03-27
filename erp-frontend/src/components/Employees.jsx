import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { getEmployees } from '../services/api';
import api from '../services/api';
import {
  Mail, Phone, Briefcase, Plus, Pencil, Trash2,
  X, Save, Eye, EyeOff, Search, ChevronDown
} from 'lucide-react';

// ── Role badge ────────────────────────────────────────────────────────────────
const ROLE_STYLES = {
  ceo:      { bg: '#f3e8ff', text: '#7c3aed', label: 'CEO' },
  manager:  { bg: '#dbeafe', text: '#1d4ed8', label: 'Manager' },
  employee: { bg: '#dcfce7', text: '#15803d', label: 'Employé' },
  rh:       { bg: '#fef3c7', text: '#b45309', label: 'RH' },
  admin:    { bg: '#ffe4e6', text: '#e11d48', label: 'Admin' },
};

const RoleBadge = ({ role }) => {
  const s = ROLE_STYLES[role] || ROLE_STYLES.employee;
  return (
    <span style={{
      background: s.bg, color: s.text,
      padding: '3px 10px', borderRadius: 20,
      fontSize: 11, fontWeight: 700, whiteSpace: 'nowrap',
    }}>
      {s.label}
    </span>
  );
};

// ── Modal ─────────────────────────────────────────────────────────────────────
const DEPT_OPTIONS = ['Finance', 'Projects', 'Operations', 'Human Resources', 'IT', 'Executive'];
const ROLE_OPTIONS = ['employee', 'manager', 'rh', 'admin', 'ceo'];

const EmployeeModal = ({ mode, employee, onClose, onSave }) => {
  const isCreate = mode === 'create';
  const [form, setForm] = useState(isCreate ? {
    employee_id: '', username: '', password: '', first_name: '', last_name: '',
    email: '', phone: '', position: '', department: 'Projects', role: 'employee',
    hire_date: new Date().toISOString().split('T')[0], salary_eur: '', manager_id: '',
  } : {
    first_name: employee.first_name, last_name: employee.last_name,
    email: employee.email, phone: employee.phone || '',
    position: employee.position, department: employee.department,
    role: employee.role, salary_eur: employee.salary_eur || '',
    manager_id: employee.manager_id || '',
  });
  const [showPwd, setShowPwd] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    setError('');
    setSaving(true);
    try {
      if (isCreate) {
        await api.post('/employees', form);
      } else {
        await api.put(`/employees/${employee.employee_id}`, form);
      }
      onSave();
    } catch (e) {
      setError(e.response?.data?.detail || 'Une erreur est survenue');
    } finally {
      setSaving(false);
    }
  };

  const Field = ({ label, name, type = 'text', options }) => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      <label style={{ fontSize: 12, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
        {label}
      </label>
      {options ? (
        <div style={{ position: 'relative' }}>
          <select
            value={form[name]}
            onChange={e => setForm(f => ({ ...f, [name]: e.target.value }))}
            style={{ width: '100%', padding: '9px 32px 9px 12px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 14, background: '#f8fafc', appearance: 'none', cursor: 'pointer' }}
          >
            {options.map(o => <option key={o} value={o}>{o}</option>)}
          </select>
          <ChevronDown size={14} style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', color: '#94a3b8', pointerEvents: 'none' }} />
        </div>
      ) : name === 'password' ? (
        <div style={{ position: 'relative' }}>
          <input
            type={showPwd ? 'text' : 'password'}
            value={form[name] || ''}
            onChange={e => setForm(f => ({ ...f, [name]: e.target.value }))}
            style={{ width: '100%', padding: '9px 36px 9px 12px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 14, background: '#f8fafc', boxSizing: 'border-box' }}
            placeholder="Min. 6 caractères"
          />
          <button type="button" onClick={() => setShowPwd(v => !v)}
            style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8' }}>
            {showPwd ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>
      ) : (
        <input
          type={type}
          value={form[name] || ''}
          onChange={e => setForm(f => ({ ...f, [name]: e.target.value }))}
          style={{ padding: '9px 12px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 14, background: '#f8fafc', width: '100%', boxSizing: 'border-box' }}
        />
      )}
    </div>
  );

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}>
      <div style={{ background: '#fff', borderRadius: 16, width: '100%', maxWidth: 580, maxHeight: '90vh', overflow: 'hidden', display: 'flex', flexDirection: 'column', boxShadow: '0 25px 60px rgba(0,0,0,0.2)' }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 24px', borderBottom: '1px solid #f1f5f9' }}>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1e293b', margin: 0 }}>
              {isCreate ? '➕ Nouvel employé' : `✏️ Modifier — ${employee.first_name} ${employee.last_name}`}
            </h2>
            <p style={{ fontSize: 13, color: '#64748b', margin: '3px 0 0' }}>
              {isCreate ? 'Créer un nouveau compte employé' : 'Modifier les informations de cet employé'}
            </p>
          </div>
          <button onClick={onClose} style={{ background: '#f1f5f9', border: 'none', borderRadius: 8, padding: 8, cursor: 'pointer', display: 'flex' }}>
            <X size={18} color="#64748b" />
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: '20px 24px', overflowY: 'auto', flex: 1 }}>
          {error && (
            <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, padding: '10px 14px', marginBottom: 16, color: '#dc2626', fontSize: 13 }}>
              ⚠️ {error}
            </div>
          )}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            <Field label="Prénom *" name="first_name" />
            <Field label="Nom *" name="last_name" />
            {isCreate && <Field label="ID Employé *" name="employee_id" />}
            {isCreate && <Field label="Nom d'utilisateur *" name="username" />}
            {isCreate && <Field label="Mot de passe *" name="password" />}
            <Field label="Email *" name="email" type="email" />
            <Field label="Téléphone" name="phone" />
            <Field label="Poste *" name="position" />
            <Field label="Département *" name="department" options={DEPT_OPTIONS} />
            <Field label="Rôle *" name="role" options={ROLE_OPTIONS} />
            {isCreate && <Field label="Salaire (EUR)" name="salary_eur" type="number" />}
            {isCreate && <Field label="Date d'embauche *" name="hire_date" type="date" />}
            <Field label="ID Manager" name="manager_id" />
          </div>
        </div>

        {/* Footer */}
        <div style={{ padding: '16px 24px', borderTop: '1px solid #f1f5f9', display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
          <button onClick={onClose} style={{ padding: '9px 20px', borderRadius: 8, border: '1px solid #e2e8f0', background: '#fff', color: '#64748b', fontWeight: 600, fontSize: 14, cursor: 'pointer' }}>
            Annuler
          </button>
          <button onClick={handleSubmit} disabled={saving} style={{ padding: '9px 20px', borderRadius: 8, border: 'none', background: 'linear-gradient(135deg, #4f46e5, #6366f1)', color: '#fff', fontWeight: 600, fontSize: 14, cursor: saving ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', gap: 6, opacity: saving ? 0.7 : 1 }}>
            <Save size={15} />
            {saving ? 'Sauvegarde...' : isCreate ? 'Créer' : 'Sauvegarder'}
          </button>
        </div>
      </div>
    </div>
  );
};

// ── Confirm delete modal ───────────────────────────────────────────────────────
const ConfirmDelete = ({ employee, onClose, onConfirm }) => {
  const [loading, setLoading] = useState(false);
  const handle = async () => {
    setLoading(true);
    await onConfirm();
    setLoading(false);
  };
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}>
      <div style={{ background: '#fff', borderRadius: 16, padding: 32, maxWidth: 420, width: '100%', boxShadow: '0 25px 60px rgba(0,0,0,0.2)', textAlign: 'center' }}>
        <div style={{ width: 56, height: 56, borderRadius: '50%', background: '#fef2f2', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
          <Trash2 size={24} color="#ef4444" />
        </div>
        <h3 style={{ fontSize: 18, fontWeight: 700, color: '#1e293b', margin: '0 0 8px' }}>Supprimer cet employé ?</h3>
        <p style={{ fontSize: 14, color: '#64748b', margin: '0 0 24px' }}>
          <strong>{employee.first_name} {employee.last_name}</strong> sera définitivement supprimé. Cette action est irréversible.
        </p>
        <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
          <button onClick={onClose} style={{ padding: '10px 24px', borderRadius: 8, border: '1px solid #e2e8f0', background: '#fff', color: '#64748b', fontWeight: 600, cursor: 'pointer' }}>
            Annuler
          </button>
          <button onClick={handle} disabled={loading} style={{ padding: '10px 24px', borderRadius: 8, border: 'none', background: '#ef4444', color: '#fff', fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1 }}>
            {loading ? 'Suppression...' : 'Supprimer'}
          </button>
        </div>
      </div>
    </div>
  );
};

// ── Main page ─────────────────────────────────────────────────────────────────
const Employees = () => {
  const { user } = useAuth();
  const isRH      = user?.role === 'rh';
  const isAdmin   = user?.role === 'admin';
  const canCreate = isAdmin || user?.role === 'ceo';
  const canManage = isRH || isAdmin;

  const [employees, setEmployees] = useState([]);
  const [loading, setLoading]     = useState(true);
  const [search, setSearch]       = useState('');
  const [modal, setModal]         = useState(null); // null | { mode: 'create'|'edit'|'delete', employee? }

  useEffect(() => { loadEmployees(); }, []);

  const loadEmployees = async () => {
    try {
      const res = await getEmployees();
      setEmployees(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (employee) => {
    try {
      await api.delete(`/employees/${employee.employee_id}`);
      setModal(null);
      loadEmployees();
    } catch (e) {
      alert(e.response?.data?.detail || 'Erreur lors de la suppression');
    }
  };

  const getEmployeeName = (id) => {
    const emp = employees.find(e => e.employee_id === id.trim());
    return emp ? `${emp.first_name} ${emp.last_name}` : id;
  };

  const filtered = employees.filter(e =>
    `${e.first_name} ${e.last_name} ${e.position} ${e.department} ${e.email}`
      .toLowerCase().includes(search.toLowerCase())
  );

  if (loading) return <div style={{ textAlign: 'center', padding: 40, color: '#64748b' }}>Chargement...</div>;

  return (
    <div style={{ padding: '0 0 40px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 800, color: '#1e293b', margin: 0 }}>Employés</h1>
          <p style={{ color: '#64748b', margin: '4px 0 0', fontSize: 14 }}>
            {filtered.length} employé{filtered.length > 1 ? 's' : ''} {search ? 'trouvé(s)' : 'au total'}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          {/* Search */}
          <div style={{ position: 'relative' }}>
            <Search size={15} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Rechercher..."
              style={{ padding: '9px 12px 9px 32px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 14, width: 220, background: '#f8fafc' }}
            />
          </div>
          {/* Create disabled — CEO only via backend */}
          {canCreate && (
            <button
              onClick={() => setModal({ mode: 'create' })}
              style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '9px 18px', background: 'linear-gradient(135deg, #4f46e5, #6366f1)', color: '#fff', border: 'none', borderRadius: 8, fontWeight: 600, fontSize: 14, cursor: 'pointer', boxShadow: '0 4px 14px rgba(99,102,241,0.35)', whiteSpace: 'nowrap' }}
            >
              <Plus size={16} />
              Nouvel employé
            </button>
          )}
        </div>
      </div>

      {/* Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 }}>
        {filtered.map((employee) => {
          const supervisedList = employee.supervised_employees
            ? employee.supervised_employees.split(';').filter(Boolean)
            : [];
          const projectsList = employee.assigned_projects
            ? employee.assigned_projects.split(';').filter(Boolean)
            : [];

          return (
            <div key={employee.employee_id} style={{ background: '#fff', borderRadius: 12, border: '1px solid #f1f5f9', padding: 20, boxShadow: '0 1px 3px rgba(0,0,0,0.06)', transition: 'box-shadow 0.15s' }}
              onMouseEnter={e => e.currentTarget.style.boxShadow = '0 4px 16px rgba(0,0,0,0.1)'}
              onMouseLeave={e => e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.06)'}
            >
              {/* Card header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1, minWidth: 0 }}>
                  <div style={{ width: 42, height: 42, borderRadius: '50%', background: 'linear-gradient(135deg, #e0e7ff, #c7d2fe)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 15, fontWeight: 700, color: '#4f46e5', flexShrink: 0 }}>
                    {employee.first_name[0]}{employee.last_name[0]}
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontWeight: 700, color: '#1e293b', fontSize: 15, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {employee.first_name} {employee.last_name}
                    </div>
                    <div style={{ fontSize: 12, color: '#64748b', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {employee.position}
                    </div>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
                  <RoleBadge role={employee.role} />
                  {canManage && (
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button
                        onClick={() => setModal({ mode: 'edit', employee })}
                        title="Modifier"
                        style={{ width: 30, height: 30, borderRadius: 7, border: '1px solid #e2e8f0', background: '#f8fafc', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#4f46e5' }}
                      >
                        <Pencil size={13} />
                      </button>
                      <button
                          onClick={() => setModal({ mode: 'delete', employee })}
                          title="Supprimer"
                          style={{ width: 30, height: 30, borderRadius: 7, border: '1px solid #fecaca', background: '#fef2f2', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ef4444' }}
                        >
                          <Trash2 size={13} />
                        </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Info */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 13, color: '#64748b' }}>
                  <Briefcase size={13} color="#94a3b8" />
                  {employee.department}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 13, color: '#64748b' }}>
                  <Mail size={13} color="#94a3b8" />
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{employee.email}</span>
                </div>
                {employee.phone && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 13, color: '#64748b' }}>
                    <Phone size={13} color="#94a3b8" />
                    {employee.phone}
                  </div>
                )}
              </div>

              {/* Projects */}
              {projectsList.length > 0 && (
                <div style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid #f1f5f9' }}>
                  <p style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>Projets</p>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                    {projectsList.slice(0, 3).map(pid => (
                      <span key={pid} style={{ padding: '3px 9px', background: '#eef2ff', color: '#4f46e5', borderRadius: 20, fontSize: 11, fontWeight: 600 }}>{pid}</span>
                    ))}
                    {projectsList.length > 3 && (
                      <span style={{ padding: '3px 9px', background: '#f1f5f9', color: '#64748b', borderRadius: 20, fontSize: 11 }}>+{projectsList.length - 3}</span>
                    )}
                  </div>
                </div>
              )}

              {/* Supervised */}
              {supervisedList.length > 0 && employee.role !== 'employee' && (
                <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid #f1f5f9' }}>
                  <p style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
                    Supervise ({supervisedList.length})
                  </p>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                    {supervisedList.slice(0, 4).map(id => (
                      <span key={id} style={{ padding: '3px 9px', background: '#f5f3ff', color: '#7c3aed', borderRadius: 20, fontSize: 11, fontWeight: 600 }}>
                        {getEmployeeName(id)}
                      </span>
                    ))}
                    {supervisedList.length > 4 && (
                      <span style={{ padding: '3px 9px', background: '#f1f5f9', color: '#64748b', borderRadius: 20, fontSize: 11 }}>+{supervisedList.length - 4}</span>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Modals */}
      {modal?.mode === 'create' && (
        <EmployeeModal mode="create" onClose={() => setModal(null)} onSave={() => { setModal(null); loadEmployees(); }} />
      )}
      {modal?.mode === 'edit' && (
        <EmployeeModal mode="edit" employee={modal.employee} onClose={() => setModal(null)} onSave={() => { setModal(null); loadEmployees(); }} />
      )}
      {modal?.mode === 'delete' && (
        <ConfirmDelete employee={modal.employee} onClose={() => setModal(null)} onConfirm={() => handleDelete(modal.employee)} />
      )}
    </div>
  );
};

export default Employees;