import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import AIAssistant from './AIAssistant_temp';
import {
  FileBarChart, Building2, LayoutDashboard, FolderKanban,
  Users, BarChart3, Calendar, Briefcase, CheckSquare,
  Bell, LogOut, Shield, UserCircle, Crown, AlertTriangle, Bot,
} from 'lucide-react';

const SIDEBAR_WIDTH = 260;

const Navbar = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [unreadCount, setUnreadCount] = useState(0);
  const [showAI, setShowAI] = useState(false);
  const [proactiveAlerts, setProactiveAlerts] = useState([]);
  const [alertsSeen, setAlertsSeen] = useState(false);

  useEffect(() => {
    const fetchUnreadCount = async () => {
      try {
        const response = await api.get('/notifications/unread');
        setUnreadCount(response.data.length);
      } catch (error) {
        console.error('Error fetching unread notifications:', error);
      }
    };
    
    const fetchProactive = async () => {
      try {
        const response = await api.get('/chat/proactive');
        if (response.data.alerts && response.data.alerts.length > 0) {
          setProactiveAlerts(prev => {
             const existing = new Set(prev.map(p => p.id));
             const newItems = response.data.alerts.filter(a => !existing.has(a.id));
             if (newItems.length > 0) setAlertsSeen(false);
             return [...prev, ...newItems];
          });
        }
      } catch (error) {
        console.error('Error fetching proactive alerts:', error);
      }
    };

    if (user) {
      fetchUnreadCount();
      fetchProactive(); // Let backend determine what alerts they get
      
      const interval = setInterval(() => {
        fetchUnreadCount();
        fetchProactive();
      }, 30000);
      return () => clearInterval(interval);
    }
  }, [user]);

  const handleOpenAI = () => {
    setShowAI(true);
    setAlertsSeen(true);
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const allNavItems = [
    { path: '/dashboard',      label: 'Dashboard',    icon: LayoutDashboard, roles: ['ceo', 'manager', 'employee', 'admin'] },
    { path: '/projects',       label: 'Projets',       icon: FolderKanban,    roles: ['ceo', 'manager', 'employee'] },
    { path: '/tasks',          label: 'Tâches',        icon: CheckSquare,     roles: ['ceo', 'manager', 'employee'] },
    { path: '/issues',         label: 'Incidents',     icon: AlertTriangle,   roles: ['ceo', 'manager', 'employee'] },
    { path: '/reports',        label: 'Rapports',      icon: FileBarChart,    roles: ['ceo', 'manager'] },
    { path: '/clients',        label: 'Clients',       icon: Briefcase,       roles: ['ceo', 'manager'] },
    { path: '/employees',      label: 'Employés',      icon: Users,           roles: ['ceo', 'manager', 'rh', 'admin'] },
    { path: '/kpis',           label: 'KPIs',          icon: BarChart3,       roles: ['ceo', 'manager'] },
    { path: '/leave-requests', label: 'Congés',        icon: Calendar,        roles: ['ceo', 'manager', 'employee', 'rh'] },
    { path: '/notifications',  label: 'Notifications', icon: Bell,            roles: ['ceo', 'manager', 'employee', 'rh', 'admin'], badge: unreadCount },
    { path: '/whitelist',      label: 'API Whitelist', icon: Shield,          roles: ['admin'] },
    { path: '/logs',           label: 'Journaux (Logs)',icon: FileBarChart,   roles: ['admin'] },
  ];

  const navItems = allNavItems.filter(item => item.roles.includes(user?.role));

  const roleConfig = {
    ceo:      { gradient: 'linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%)', label: 'CEO',     icon: Crown,       description: 'Accès complet'   },
    manager:  { gradient: 'linear-gradient(135deg, #0369a1 0%, #0284c7 100%)', label: 'Manager', icon: Shield,      description: "Gestion d'équipe" },
    employee: { gradient: 'linear-gradient(135deg, #15803d 0%, #16a34a 100%)', label: 'Employé', icon: UserCircle,  description: 'Accès standard'   },
    rh:       { gradient: 'linear-gradient(135deg, #b45309 0%, #d97706 100%)', label: 'RH',      icon: Users,       description: 'Gestion RH'       },
    admin:    { gradient: 'linear-gradient(135deg, #be123c 0%, #e11d48 100%)', label: 'Admin',   icon: Shield,      description: 'Administration'   },
  };

  const role = roleConfig[user?.role] || roleConfig.employee;
  const RoleIcon = role.icon;

  return (
    <>
      <aside style={{
        width: SIDEBAR_WIDTH, height: '100vh', background: '#1e293b',
        display: 'flex', flexDirection: 'column',
        position: 'fixed', top: 0, left: 0, zIndex: 200,
        overflow: 'hidden', boxShadow: '4px 0 20px rgba(0,0,0,0.2)',
      }}>

        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, height: 64, padding: '0 20px', borderBottom: '1px solid rgba(255,255,255,0.08)', flexShrink: 0 }}>
          <div style={{ width: 38, height: 38, minWidth: 38, borderRadius: 10, background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 14px rgba(99,102,241,0.5)' }}>
            <Building2 size={20} color="#fff" />
          </div>
          <div>
            <div style={{ color: '#ffffff', fontWeight: 800, fontSize: 15, letterSpacing: '-0.02em' }}>Construction</div>
            <div style={{ color: '#818cf8', fontWeight: 700, fontSize: 10, letterSpacing: '0.15em' }}>ERP SYSTEM</div>
          </div>
        </div>

        {/* User Role Banner */}
        <div style={{ margin: '12px 12px 4px', borderRadius: 12, background: role.gradient, padding: '14px 16px', flexShrink: 0, boxShadow: '0 4px 16px rgba(0,0,0,0.2)', position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', top: -20, right: -20, width: 80, height: 80, borderRadius: '50%', background: 'rgba(255,255,255,0.08)' }} />
          <div style={{ position: 'absolute', bottom: -30, right: 10, width: 70, height: 70, borderRadius: '50%', background: 'rgba(255,255,255,0.05)' }} />
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, position: 'relative' }}>
            <div style={{ width: 42, height: 42, minWidth: 42, borderRadius: '50%', background: 'rgba(255,255,255,0.2)', border: '2px solid rgba(255,255,255,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 800, fontSize: 15 }}>
              {user?.first_name?.[0]}{user?.last_name?.[0]}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ color: '#ffffff', fontWeight: 700, fontSize: 14, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{user?.first_name} {user?.last_name}</div>
              <div style={{ color: 'rgba(255,255,255,0.75)', fontSize: 11, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{user?.username}</div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
              <div style={{ background: 'rgba(255,255,255,0.2)', border: '1px solid rgba(255,255,255,0.3)', borderRadius: 8, padding: '4px 8px', display: 'flex', alignItems: 'center', gap: 4 }}>
                <RoleIcon size={12} color="#fff" />
                <span style={{ color: '#ffffff', fontSize: 11, fontWeight: 800, letterSpacing: '0.05em' }}>{role.label}</span>
              </div>
              <span style={{ color: 'rgba(255,255,255,0.65)', fontSize: 9, fontWeight: 500, whiteSpace: 'nowrap' }}>{role.description}</span>
            </div>
          </div>
        </div>

        {/* Nav Items */}
        <nav style={{ flex: 1, padding: '8px 12px', overflowY: 'auto', overflowX: 'hidden' }}>
          <div style={{ color: '#64748b', fontSize: 10, fontWeight: 700, letterSpacing: '0.15em', padding: '8px 8px 8px' }}>NAVIGATION</div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link key={item.path} to={item.path} style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '10px 12px', borderRadius: 9, marginBottom: 2,
                textDecoration: 'none',
                background: isActive ? 'rgba(99,102,241,0.2)' : 'transparent',
                color: isActive ? '#a5b4fc' : '#94a3b8',
                transition: 'background 0.15s, color 0.15s',
                fontWeight: isActive ? 600 : 400, fontSize: 14, whiteSpace: 'nowrap',
                borderLeft: isActive ? '3px solid #6366f1' : '3px solid transparent',
              }}
                onMouseEnter={e => { if (!isActive) { e.currentTarget.style.background = 'rgba(255,255,255,0.07)'; e.currentTarget.style.color = '#e2e8f0'; } }}
                onMouseLeave={e => { if (!isActive) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#94a3b8'; } }}
              >
                <span style={{ flexShrink: 0, minWidth: 22, display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
                  <Icon size={19} />
                  {item.badge > 0 && (
                    <span style={{ position: 'absolute', top: -5, right: -5, background: '#ef4444', color: '#fff', fontSize: 9, fontWeight: 700, borderRadius: '50%', width: 15, height: 15, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      {item.badge > 9 ? '9+' : item.badge}
                    </span>
                  )}
                </span>
                <span style={{ flex: 1 }}>{item.label}</span>
                {item.badge > 0 && (
                  <span style={{ background: '#ef4444', color: '#fff', fontSize: 11, fontWeight: 700, borderRadius: 20, padding: '2px 7px' }}>
                    {item.badge > 9 ? '9+' : item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Logout */}
        <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)', padding: '10px 12px', flexShrink: 0 }}>
          <button onClick={handleLogout} style={{ display: 'flex', alignItems: 'center', gap: 10, width: '100%', padding: '11px 12px', background: 'transparent', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 9, color: '#94a3b8', cursor: 'pointer', fontSize: 14, fontWeight: 500, transition: 'all 0.15s' }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(239,68,68,0.12)'; e.currentTarget.style.color = '#fca5a5'; e.currentTarget.style.borderColor = 'rgba(239,68,68,0.3)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#94a3b8'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'; }}
          >
            <LogOut size={18} />
            <span>Déconnexion</span>
          </button>
        </div>
      </aside>

      {/* ── Floating AI Button (all roles) ── */}
      {user && (
        <>
          <style>{`
            @keyframes fabIn { from { opacity: 0; transform: scale(0.7) translateY(12px); } to { opacity: 1; transform: scale(1) translateY(0); } }
            .ai-fab-wrap { animation: fabIn 0.35s cubic-bezier(.34,1.56,.64,1) both; position: fixed; bottom: 32px; right: 32px; z-index: 300; display: flex; align-items: center; gap: 10px; }
            .ai-fab-label { opacity: 0; transform: translateX(8px); transition: opacity 0.2s, transform 0.2s; pointer-events: none; }
            .ai-fab-wrap:hover .ai-fab-label { opacity: 1; transform: translateX(0); }
          `}</style>

          <div className="ai-fab-wrap">
            <span className="ai-fab-label" style={{
              background: '#1e293b',
              color: '#e2e8f0',
              fontSize: 13,
              fontWeight: 600,
              padding: '7px 14px',
              borderRadius: 10,
              whiteSpace: 'nowrap',
              boxShadow: '0 4px 16px rgba(0,0,0,0.25)',
              border: '1px solid rgba(255,255,255,0.08)',
            }}>
              Assistant IA
            </span>

            <button
              onClick={handleOpenAI}
              title="Assistant IA"
              style={{
                width: 58,
                height: 58,
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #4f46e5, #818cf8)',
                border: '2px solid rgba(255,255,255,0.2)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 6px 24px rgba(99,102,241,0.45)',
                transition: 'transform 0.2s cubic-bezier(.34,1.56,.64,1), box-shadow 0.2s',
                flexShrink: 0,
              }}
              onMouseEnter={e => {
                e.currentTarget.style.transform = 'scale(1.1)';
                e.currentTarget.style.boxShadow = '0 8px 32px rgba(99,102,241,0.65)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.transform = 'scale(1)';
                e.currentTarget.style.boxShadow = '0 6px 24px rgba(99,102,241,0.45)';
              }}
            >
              <Bot size={26} color="#fff" strokeWidth={1.8} />
              {proactiveAlerts.length > 0 && !alertsSeen && (
                <span style={{ position: 'absolute', top: -4, right: -4, background: '#ef4444', color: '#fff', fontSize: 11, fontWeight: 700, borderRadius: '50%', width: 20, height: 20, display: 'flex', alignItems: 'center', justifyContent: 'center', border: '2px solid #1e293b' }}>
                  {proactiveAlerts.length > 9 ? '9+' : proactiveAlerts.length}
                </span>
              )}
            </button>
          </div>

          {showAI && <AIAssistant onClose={() => setShowAI(false)} proactiveAlerts={proactiveAlerts} />}
        </>
      )}
    </>
  );
};

export default Navbar;