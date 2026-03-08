import React, { useState, useEffect } from 'react';
import { 
  FileBarChart, 
  Download, 
  Calendar, 
  Filter,
  TrendingUp,
  Users,
  DollarSign,
  CheckSquare,
  Plus,
  RefreshCw,
  Lock
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import './Reports.css';

const Reports = () => {
  const { user, isCEO, isManager } = useAuth();
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [generating, setGenerating] = useState(false);

  const currentYear = new Date().getFullYear();

  // ✅ "Rapport Personnalisé" only for CEO
  const allReportTypes = [
    { value: 'project_status',       label: 'Rapport de Projet',   icon: TrendingUp,   color: '#3b82f6' },
    { value: 'employee_performance', label: 'Rapport Employé',      icon: Users,        color: '#8b5cf6' },
    { value: 'budget',               label: 'Rapport Financier',    icon: DollarSign,   color: '#10b981' },
    { value: 'task_completion',      label: 'Rapport KPI',          icon: CheckSquare,  color: '#f59e0b' },
    { value: 'custom',               label: 'Rapport Personnalisé', icon: FileBarChart, color: '#6366f1', ceoOnly: true },
  ];

  const reportTypes = allReportTypes.filter(t => !t.ceoOnly || isCEO);

  const [formData, setFormData] = useState({
    report_type:  'project_status',
    title:        '',
    period_start: `${currentYear}-01-01`,
    period_end:   `${currentYear}-12-31`,
    filters:      {},
    parameters:   {}
  });

  useEffect(() => {
    if (user) {
      // ✅ FIX: don't fetch at all for employees, just stop loading
      if (!isCEO && !isManager) {
        setLoading(false);
        return;
      }
      fetchReports();
    }
  }, [user]);

  const fetchReports = async () => {
    try {
      setLoading(true);
      const response = await api.get('/reports');
      setReports(response.data);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors du chargement des rapports');
      console.error('Error fetching reports:', err);
    } finally {
      setLoading(false);
    }
  };

  const generateReport = async (e) => {
    e.preventDefault();
    try {
      setGenerating(true);

      const reportData = {
        report_id:    `REP${Date.now()}`,
        report_type:  formData.report_type,
        title:        formData.title || `Rapport ${getReportLabel(formData.report_type)} - ${new Date().toLocaleDateString('fr-FR')}`,
        period_start: formData.period_start,
        period_end:   formData.period_end,
        generated_by: user?.employee_id || 'E001',
        filters:      JSON.stringify(formData.filters),
        parameters:   JSON.stringify(formData.parameters)
      };

      await api.post('/reports/generate', reportData);
      await fetchReports();
      handleCloseModal();
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors de la génération');
      console.error('Error generating report:', err);
    } finally {
      setGenerating(false);
    }
  };

  const handleCloseModal = () => {
    const yr = new Date().getFullYear();
    setShowModal(false);
    setFormData({
      report_type:  'project_status',
      title:        '',
      period_start: `${yr}-01-01`,
      period_end:   `${yr}-12-31`,
      filters:      {},
      parameters:   {}
    });
  };

  const getReportIcon = (type) => {
    const reportType = allReportTypes.find(rt => rt.value === type);
    if (reportType) {
      const Icon = reportType.icon;
      return <Icon size={20} style={{ color: reportType.color }} />;
    }
    return <FileBarChart size={20} />;
  };

  const getReportColor = (type) => {
    const reportType = allReportTypes.find(rt => rt.value === type);
    return reportType ? reportType.color : '#6366f1';
  };

  const getReportLabel = (type) => {
    const reportType = allReportTypes.find(rt => rt.value === type);
    return reportType ? reportType.label : type;
  };

  const formatDate = (dateString) => {
    if (!dateString) return '—';
    return new Date(dateString).toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    });
  };

  const downloadReport = (report) => {
    try {
      const content = report.content ? JSON.parse(report.content) : {};
      const blob = new Blob([JSON.stringify(content, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${report.title || report.report_id}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert(`Téléchargement du rapport: ${report.title}`);
    }
  };

  // ✅ FIX: guard BEFORE loading check — employee sees this immediately
  if (!loading && !isCEO && !isManager) {
    return (
      <div className="reports-container">
        <div className="empty-state">
          <Lock size={64} style={{ color: '#9ca3af' }} />
          <h3>Accès refusé</h3>
          <p>Seuls les managers et le CEO peuvent accéder aux rapports.</p>
        </div>
      </div>
    );
  }

  if (loading) return <div className="loading">Chargement des rapports...</div>;

  return (
    <div className="reports-container">
      {error && (
        <div className="error-banner">
          ⚠️ {error}
          <button onClick={() => setError(null)}>✕</button>
        </div>
      )}

      <div className="reports-header">
        <div className="header-left">
          <h1>
            <FileBarChart size={32} />
            Rapports
          </h1>
          <p className="subtitle">
            {isCEO
              ? "Tous les rapports de l'entreprise"
              : 'Vos rapports générés'}
          </p>
        </div>
        <div className="header-actions">
          <button className="btn-secondary" onClick={fetchReports}>
            <RefreshCw size={18} />
            Actualiser
          </button>
          {(isCEO || isManager) && (
            <button className="btn-primary" onClick={() => setShowModal(true)}>
              <Plus size={18} />
              Générer un rapport
            </button>
          )}
        </div>
      </div>

      {/* Quick Stats */}
      <div className="report-stats">
        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#dbeafe' }}>
            <FileBarChart size={24} style={{ color: '#3b82f6' }} />
          </div>
          <div className="stat-info">
            <div className="stat-value">{reports.length}</div>
            <div className="stat-label">
              {isCEO ? 'Rapports totaux' : 'Mes rapports'}
            </div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#dcfce7' }}>
            <CheckSquare size={24} style={{ color: '#10b981' }} />
          </div>
          <div className="stat-info">
            <div className="stat-value">
              {reports.filter(r => r.status === 'Completed').length}
            </div>
            <div className="stat-label">Complétés</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#fef3c7' }}>
            <Calendar size={24} style={{ color: '#f59e0b' }} />
          </div>
          <div className="stat-info">
            <div className="stat-value">
              {reports.filter(r => {
                const date = new Date(r.generation_date);
                const now = new Date();
                return date.getMonth() === now.getMonth() &&
                       date.getFullYear() === now.getFullYear();
              }).length}
            </div>
            <div className="stat-label">Ce mois</div>
          </div>
        </div>
      </div>

      {/* Reports List */}
      <div className="reports-list">
        {reports.length === 0 ? (
          <div className="empty-state">
            <FileBarChart size={64} />
            <h3>Aucun rapport généré</h3>
            <p>Cliquez sur "Générer un rapport" pour commencer</p>
          </div>
        ) : (
          <div className="reports-grid">
            {reports.map(report => (
              <div key={report.report_id} className="report-card">
                <div className="report-header-card">
                  <div
                    className="report-icon-wrapper"
                    style={{ background: `${getReportColor(report.report_type)}15` }}
                  >
                    {getReportIcon(report.report_type)}
                  </div>
                  <div className="report-status">
                    <span className={`status-badge status-${report.status?.toLowerCase()}`}>
                      {report.status}
                    </span>
                  </div>
                </div>

                <div className="report-content">
                  <h3>{report.title}</h3>
                  <div className="report-meta">
                    <span className="report-type">{getReportLabel(report.report_type)}</span>
                    <span className="report-date">
                      <Calendar size={14} />
                      {formatDate(report.generation_date)}
                    </span>
                  </div>

                  {/* CEO sees who generated each report */}
                  {isCEO && report.generated_by && (
                    <div className="report-generated-by">
                      <Users size={12} />
                      <span>Par: {report.generated_by_name || report.generated_by}</span>

                    </div>
                  )}

                  <div className="report-period">
                    <strong>Période :</strong>
                    <br />
                    {formatDate(report.period_start)} → {formatDate(report.period_end)}
                  </div>

                  {/* Summary stats from content JSON */}
                  {report.content && (() => {
                    try {
                      const c = JSON.parse(report.content);
                      return (
                        <div className="report-summary">
                          {c.total_projects  !== undefined && <span>📁 {c.total_projects} projets</span>}
                          {c.total_employees !== undefined && <span>👥 {c.total_employees} employés</span>}
                          {c.total_budget    !== undefined && <span>💶 {c.total_budget?.toLocaleString()} € budget</span>}
                          {c.total_tasks     !== undefined && <span>✅ {c.total_tasks} tâches</span>}
                          {c.completion_rate !== undefined && <span>📊 {c.completion_rate}% complété</span>}
                          {c.total_variance  !== undefined && (
                            <span style={{ color: c.total_variance > 0 ? '#ef4444' : '#10b981' }}>
                              {c.total_variance > 0 ? '⚠️' : '✅'} Variance: {c.total_variance?.toLocaleString()} €
                            </span>
                          )}
                        </div>
                      );
                    } catch {
                      return null;
                    }
                  })()}

                  {report.filters && report.filters !== '{}' && (
                    <div className="report-filters">
                      <Filter size={14} />
                      Filtres appliqués
                    </div>
                  )}
                </div>

                <div className="report-actions">
                  <button
                    className="btn-download"
                    onClick={() => downloadReport(report)}
                    disabled={report.status !== 'Completed'}
                  >
                    <Download size={16} />
                    Télécharger
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal Generate Report */}
      {showModal && (
        <div className="modal-overlay" onClick={handleCloseModal}>
          <div className="modal-content modal-large" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>
                <FileBarChart size={28} />
                Générer un nouveau rapport
              </h2>
              <button className="btn-close" onClick={handleCloseModal}>✕</button>
            </div>

            <form onSubmit={generateReport}>
              <div className="form-section">
                <h3>Type de rapport</h3>
                {/* reportTypes already filtered — manager won't see "custom" */}
                <div className="report-types-grid">
                  {reportTypes.map(type => {
                    const Icon = type.icon;
                    return (
                      <label
                        key={type.value}
                        className={`report-type-option ${formData.report_type === type.value ? 'selected' : ''}`}
                      >
                        <input
                          type="radio"
                          name="report_type"
                          value={type.value}
                          checked={formData.report_type === type.value}
                          onChange={(e) => setFormData({ ...formData, report_type: e.target.value })}
                        />
                        <div className="report-type-card">
                          <Icon size={24} style={{ color: type.color }} />
                          <span>{type.label}</span>
                        </div>
                      </label>
                    );
                  })}
                </div>

                {isManager && !isCEO && (
                  <p style={{ fontSize: '0.8rem', color: '#6b7280', marginTop: '8px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Lock size={12} />
                    Le rapport personnalisé (données complètes) est réservé au CEO.
                  </p>
                )}
              </div>

              <div className="form-section">
                <h3>Informations du rapport</h3>

                <div className="form-group">
                  <label>Titre du rapport (optionnel)</label>
                  <input
                    type="text"
                    value={formData.title}
                    onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                    placeholder="Ex: Rapport mensuel février 2026"
                  />
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label>Date de début *</label>
                    <input
                      type="date"
                      value={formData.period_start}
                      onChange={(e) => setFormData({ ...formData, period_start: e.target.value })}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label>Date de fin *</label>
                    <input
                      type="date"
                      value={formData.period_end}
                      onChange={(e) => setFormData({ ...formData, period_end: e.target.value })}
                      required
                    />
                  </div>
                </div>

                <p style={{ fontSize: '0.8rem', color: '#6b7280', marginTop: '6px' }}>
                  💡 Les dates filtrent les projets/tâches actifs sur cette période.
                  Par défaut l'année en cours ({currentYear}) est sélectionnée.
                </p>
              </div>

              <div className="modal-footer">
                <button type="button" onClick={handleCloseModal} className="btn-secondary">
                  Annuler
                </button>
                <button type="submit" className="btn-primary" disabled={generating}>
                  {generating ? (
                    <>
                      <RefreshCw size={18} className="spin" />
                      Génération en cours...
                    </>
                  ) : (
                    <>
                      <FileBarChart size={18} />
                      Générer le rapport
                    </>
                  )}
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