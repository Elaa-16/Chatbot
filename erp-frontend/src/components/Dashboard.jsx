import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { getStats, getProjects, getKPIs } from '../services/api';
import AIAssistant from './AIAssistant_temp';  // ✅ déjà correct
import { useNavigate } from 'react-router-dom';
import {
  TrendingUp, TrendingDown, Briefcase, DollarSign,
  Target, AlertCircle, Bot, CheckCircle, Clock,
  MapPin, BarChart2, ArrowRight
} from 'lucide-react';

const Dashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [projects, setProjects] = useState([]);
  const [kpis, setKPIs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAI, setShowAI] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [statsRes, projectsRes, kpisRes] = await Promise.all([
        getStats(),
        getProjects(),
        getKPIs(),
      ]);
      setStats(statsRes.data);
      setProjects(projectsRes.data);
      setKPIs(kpisRes.data);
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={styles.loadingWrapper}>
        <div style={styles.spinner} />
        <p style={styles.loadingText}>Chargement du tableau de bord...</p>
      </div>
    );
  }

  const budgetVariance = stats?.total_budget && stats?.total_actual_cost
    ? ((stats.total_actual_cost - stats.total_budget) / stats.total_budget * 100).toFixed(2)
    : 0;

 // ✅ Bloc complet — remplacer les 4 lignes de variables
const delayedProjects = kpis.filter((k, i, arr) =>
  (k.schedule_variance_days || 0) > 0 &&
  arr.findIndex(x => x.project_id === k.project_id) === i
).length;

const onTrackProjects = projects.filter(p =>
  p.status === 'In Progress' &&
  !kpis.some(k => k.project_id === p.project_id && (k.schedule_variance_days || 0) > 0)
).length;

const completedProjects = projects.filter(p => p.status === 'Completed').length;

const criticalProjects = kpis.filter((k, i, arr) =>
  (k.schedule_variance_days || 0) > 30 &&
  arr.findIndex(x => x.project_id === k.project_id) === i
).length;
  const hasKpiAlerts = kpis.some(kpi => kpi.safety_incidents > 2 || kpi.quality_score < 85);

  return (
    <div style={styles.page}>

      {/* ── Header ── */}
      <div style={styles.pageHeader}>
        <div>
          <h1 style={styles.pageTitle}>
            Bienvenue, {user?.first_name} {user?.last_name} !
          </h1>
          <p style={styles.pageSubtitle}>
            Voici un aperçu de vos projets et indicateurs de performance
          </p>
        </div>
        <button style={styles.aiBtn} onClick={() => setShowAI(true)}>
          <Bot size={18} />
          Assistant IA
        </button>
      </div>

      {/* ── Welcome Banner ── */}
      <div style={styles.banner}>
        <div style={styles.bannerContent}>
          <div style={styles.bannerIcon}>
            <BarChart2 size={28} color="#fff" />
          </div>
          <div>
            <div style={styles.bannerTitle}>Bienvenue, {user?.first_name} {user?.last_name} !</div>
            <div style={styles.bannerSub}>Voici un aperçu de vos projets et indicateurs de performance</div>
          </div>
        </div>
        <div style={styles.bannerDecoration} />
      </div>

      {/* ── KPI Alert ── */}
      {hasKpiAlerts && (
        <div style={styles.alert}>
          <AlertCircle size={18} color="#dc2626" />
          <div>
            <strong style={{ color: '#991b1b' }}>Alertes KPI détectées</strong>
            <p style={styles.alertText}>
              Certains projets ont des incidents de sécurité élevés ou des scores de qualité faibles.
              Consultez la section KPIs pour plus de détails.
            </p>
          </div>
        </div>
      )}

      {/* ── Stat Cards ── */}
      <div style={styles.statsGrid}>
        {[
          {
            label: 'Total Projects',
            value: stats?.total_projects || 0,
            icon: <Briefcase size={22} />,
            accent: '#3b82f6',
            bg: '#eff6ff',
          },
          {
            label: 'Budget Total',
            value: `${(stats?.total_budget / 1000000 || 0).toFixed(1)}M €`,
            icon: <DollarSign size={22} />,
            accent: '#10b981',
            bg: '#ecfdf5',
          },
          {
            label: 'Avancement Moyen',
            value: `${(stats?.avg_completion || 0).toFixed(0)}%`,
            icon: <Target size={22} />,
            accent: '#8b5cf6',
            bg: '#f5f3ff',
          },
          {
            label: 'Variance Budget',
            value: `${budgetVariance}%`,
            icon: budgetVariance < 0 ? <TrendingDown size={22} /> : <TrendingUp size={22} />,
            accent: budgetVariance < 0 ? '#10b981' : '#ef4444',
            bg: budgetVariance < 0 ? '#ecfdf5' : '#fef2f2',
          },
        ].map((card, i) => (
          <div key={i} style={styles.statCard}>
            <div style={styles.statCardTop}>
              <div>
                <p style={styles.statLabel}>{card.label}</p>
                <p style={{ ...styles.statValue, color: card.accent }}>{card.value}</p>
              </div>
              <div style={{ ...styles.statIcon, backgroundColor: card.bg, color: card.accent }}>
                {card.icon}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* ── Bottom Grid ── */}
      <div style={styles.bottomGrid}>

        {/* Project Status */}
        <div style={styles.card}>
          <div style={styles.cardHeader}>
            <h2 style={styles.cardTitle}>État des Projets</h2>
          </div>
          <div style={styles.statusList}>
            {[
              { label: 'En bonne voie', count: onTrackProjects, color: '#10b981', bg: '#ecfdf5', icon: <CheckCircle size={16} color="#10b981" /> },
              { label: 'En retard', count: delayedProjects, color: '#f59e0b', bg: '#fffbeb', icon: <Clock size={16} color="#f59e0b" /> },
              { label: 'Terminés', count: completedProjects, color: '#3b82f6', bg: '#eff6ff', icon: <CheckCircle size={16} color="#3b82f6" /> },
              { label: 'Critiques', count: criticalProjects, color: '#ef4444', bg: '#fef2f2', icon: <AlertCircle size={16} color="#ef4444" /> },
            ].map((item, i) => (
              <div key={i} style={{ ...styles.statusItem, backgroundColor: item.bg }}>
                <div style={styles.statusLeft}>
                  {item.icon}
                  <span style={{ ...styles.statusLabel, color: item.color }}>{item.label}</span>
                </div>
                <span style={{ ...styles.statusCount, color: item.color }}>{item.count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Projects */}
        <div style={styles.card}>
          <div style={styles.cardHeader}>
            <h2 style={styles.cardTitle}>Projets Récents</h2>
              <button style={styles.seeAllBtn} onClick={() => navigate('/projects')}>
    Voir tout <ArrowRight size={14} />
  </button>
          </div>
          <div style={styles.projectList}>
            {projects.slice(0, 5).map((project) => (
              <div key={project.project_id} style={styles.projectItem}>
                <div style={styles.projectInfo}>
                  <div style={styles.projectName}>{project.project_name}</div>
                  <div style={styles.projectLocation}>
                    <MapPin size={11} color="#94a3b8" />
                    {project.location}
                  </div>
                </div>
                <div style={styles.projectRight}>
                  <div style={styles.progressBarWrapper}>
                    <div
                      style={{
                        ...styles.progressBarFill,
                        width: `${project.completion_percentage}%`,
                        backgroundColor: project.completion_percentage >= 70
                          ? '#10b981'
                          : project.completion_percentage >= 40
                          ? '#f59e0b'
                          : '#ef4444',
                      }}
                    />
                  </div>
                  <div style={styles.projectMeta}>
                    <span style={styles.projectPct}>{project.completion_percentage}%</span>
                    <span style={styles.projectStatus}>{project.status}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── AI Assistant Modal ── */}
      {showAI && <AIAssistant onClose={() => setShowAI(false)} />}

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
};

// ─── Styles ───────────────────────────────────────────────────────────────────
const styles = {
  page: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
    fontFamily: "'Segoe UI', system-ui, sans-serif",
  },

  // Loading
  loadingWrapper: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '260px',
    gap: '16px',
  },
  spinner: {
    width: '44px',
    height: '44px',
    border: '3px solid #e2e8f0',
    borderTop: '3px solid #6d28d9',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  loadingText: {
    color: '#64748b',
    fontSize: '14px',
  },

  // Header
  pageHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  pageTitle: {
    fontSize: '26px',
    fontWeight: 700,
    color: '#0f172a',
    margin: 0,
  },
  pageSubtitle: {
    color: '#64748b',
    fontSize: '14px',
    margin: '4px 0 0',
  },
  aiBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    background: 'linear-gradient(135deg, #6d28d9, #7c3aed)',
    color: '#fff',
    border: 'none',
    borderRadius: '12px',
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
    boxShadow: '0 4px 14px rgba(109,40,217,0.35)',
    transition: 'transform 0.15s, box-shadow 0.15s',
  },

  // Banner
  banner: {
    position: 'relative',
    background: 'linear-gradient(135deg, #6d28d9 0%, #7c3aed 50%, #a855f7 100%)',
    borderRadius: '16px',
    padding: '24px 28px',
    overflow: 'hidden',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  bannerContent: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    zIndex: 1,
  },
  bannerIcon: {
    width: '52px',
    height: '52px',
    borderRadius: '14px',
    backgroundColor: 'rgba(255,255,255,0.2)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  bannerTitle: {
    color: '#fff',
    fontWeight: 700,
    fontSize: '18px',
  },
  bannerSub: {
    color: 'rgba(255,255,255,0.75)',
    fontSize: '13px',
    marginTop: '4px',
  },
  bannerDecoration: {
    position: 'absolute',
    right: '-40px',
    top: '-40px',
    width: '180px',
    height: '180px',
    borderRadius: '50%',
    backgroundColor: 'rgba(255,255,255,0.08)',
  },

  // Alert
  alert: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '12px',
    backgroundColor: '#fef2f2',
    border: '1px solid #fecaca',
    borderLeft: '4px solid #dc2626',
    borderRadius: '12px',
    padding: '14px 18px',
  },
  alertText: {
    color: '#b91c1c',
    fontSize: '13px',
    margin: '4px 0 0',
  },

  // Stats Grid
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '16px',
  },
  statCard: {
    backgroundColor: '#fff',
    borderRadius: '14px',
    padding: '20px',
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
    border: '1px solid #f1f5f9',
  },
  statCardTop: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  statLabel: {
    fontSize: '13px',
    color: '#64748b',
    fontWeight: 500,
    margin: 0,
  },
  statValue: {
    fontSize: '26px',
    fontWeight: 700,
    margin: '6px 0 0',
  },
  statIcon: {
    width: '46px',
    height: '46px',
    borderRadius: '12px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },

  // Bottom Grid
  bottomGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '20px',
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: '14px',
    padding: '22px',
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
    border: '1px solid #f1f5f9',
  },
  cardHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '16px',
  },
  cardTitle: {
    fontSize: '16px',
    fontWeight: 700,
    color: '#0f172a',
    margin: 0,
  },
  seeAllBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    background: 'none',
    border: 'none',
    color: '#7c3aed',
    fontSize: '13px',
    fontWeight: 500,
    cursor: 'pointer',
  },

  // Status list
  statusList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  statusItem: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '12px 16px',
    borderRadius: '10px',
  },
  statusLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  statusLabel: {
    fontWeight: 500,
    fontSize: '14px',
  },
  statusCount: {
    fontSize: '22px',
    fontWeight: 700,
  },

  // Project list
  projectList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  projectItem: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '16px',
    padding: '10px 12px',
    borderRadius: '10px',
    backgroundColor: '#f8fafc',
    border: '1px solid #f1f5f9',
  },
  projectInfo: {
    flex: 1,
    minWidth: 0,
  },
  projectName: {
    fontWeight: 600,
    fontSize: '13px',
    color: '#0f172a',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  projectLocation: {
    display: 'flex',
    alignItems: 'center',
    gap: '3px',
    fontSize: '11px',
    color: '#94a3b8',
    marginTop: '3px',
  },
  projectRight: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-end',
    gap: '4px',
    minWidth: '100px',
  },
  progressBarWrapper: {
    width: '100px',
    height: '5px',
    backgroundColor: '#e2e8f0',
    borderRadius: '99px',
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    borderRadius: '99px',
    transition: 'width 0.5s ease',
  },
  projectMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  projectPct: {
    fontSize: '12px',
    fontWeight: 700,
    color: '#475569',
  },
  projectStatus: {
    fontSize: '10px',
    color: '#94a3b8',
  },
};

export default Dashboard;