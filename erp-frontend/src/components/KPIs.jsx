import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { getKPIs } from '../services/api';
import { TrendingUp, TrendingDown, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';

const KPIs = () => {
  const { user } = useAuth();
  const [kpis, setKPIs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedProject, setSelectedProject] = useState('all');

  useEffect(() => {
    loadKPIs();
  }, []);

  const loadKPIs = async () => {
    try {
      const response = await getKPIs();
      setKPIs(response.data);
    } catch (error) {
      console.error('Error loading KPIs:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-center py-8">Chargement...</div>;
  }

  const uniqueProjects = [...new Set(kpis.map(kpi => kpi.project_id))];
  const filteredKPIs = selectedProject === 'all' 
    ? kpis 
    : kpis.filter(kpi => kpi.project_id === selectedProject);

  const getRiskColor = (risk) => {
    const colors = {
      'Low': 'bg-green-100 text-green-800',
      'Medium': 'bg-yellow-100 text-yellow-800',
      'High': 'bg-red-100 text-red-800',
    };
    return colors[risk] || 'bg-gray-100 text-gray-800';
  };

  const getVarianceIcon = (variance) => {
    if (variance < -5) return <TrendingDown className="w-5 h-5 text-green-500" />;
    if (variance > 5) return <TrendingUp className="w-5 h-5 text-red-500" />;
    return <CheckCircle className="w-5 h-5 text-blue-500" />;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">KPIs</h1>
          <p className="text-gray-600 mt-1">{filteredKPIs.length} indicateur(s) de performance</p>
        </div>

        {/* Filter */}
        <select
          value={selectedProject}
          onChange={(e) => setSelectedProject(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
        >
          <option value="all">Tous les projets</option>
          {uniqueProjects.map(projectId => (
            <option key={projectId} value={projectId}>{projectId}</option>
          ))}
        </select>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-sm text-gray-600">Score Qualité Moyen</div>
          <div className="text-2xl font-bold text-indigo-600 mt-1">
            {(filteredKPIs.reduce((sum, kpi) => sum + (kpi.quality_score || 0), 0) / filteredKPIs.length).toFixed(0)}
          </div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-sm text-gray-600">Incidents Totaux</div>
          <div className="text-2xl font-bold text-red-600 mt-1">
            {filteredKPIs.reduce((sum, kpi) => sum + (kpi.safety_incidents || 0), 0)}
          </div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-sm text-gray-600">Satisfaction Moyenne</div>
          <div className="text-2xl font-bold text-green-600 mt-1">
            {(filteredKPIs.reduce((sum, kpi) => sum + (kpi.client_satisfaction_score || 0), 0) / filteredKPIs.length).toFixed(1)}/5
          </div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-sm text-gray-600">Projets à Risque</div>
          <div className="text-2xl font-bold text-orange-600 mt-1">
            {filteredKPIs.filter(kpi => kpi.risk_level === 'High').length}
          </div>
        </div>
      </div>

      {/* KPIs List */}
      <div className="space-y-4">
        {filteredKPIs.map((kpi) => (
          <div key={kpi.kpi_id} className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-lg font-bold text-gray-900">{kpi.project_name}</h3>
                <p className="text-sm text-gray-600">{kpi.project_id} - {kpi.kpi_date}</p>
              </div>
              <span className={`px-3 py-1 rounded-full text-xs font-medium ${getRiskColor(kpi.risk_level)}`}>
                {kpi.risk_level} Risk
              </span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {/* Budget Variance */}
              <div className="bg-gray-50 p-3 rounded">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-gray-600">Budget Variance</span>
                  {getVarianceIcon(kpi.budget_variance_percentage)}
                </div>
                <div className={`text-lg font-bold ${
                  kpi.budget_variance_percentage < 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {kpi.budget_variance_percentage}%
                </div>
              </div>

              {/* Schedule Variance */}
              <div className="bg-gray-50 p-3 rounded">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-gray-600">Délai (jours)</span>
                  {kpi.schedule_variance_days > 10 ? (
                    <AlertTriangle className="w-4 h-4 text-orange-500" />
                  ) : (
                    <CheckCircle className="w-4 h-4 text-green-500" />
                  )}
                </div>
                <div className={`text-lg font-bold ${
                  kpi.schedule_variance_days > 10 ? 'text-orange-600' : 'text-green-600'
                }`}>
                  {kpi.schedule_variance_days > 0 ? '+' : ''}{kpi.schedule_variance_days}
                </div>
              </div>

              {/* Quality Score */}
              <div className="bg-gray-50 p-3 rounded">
                <div className="text-xs text-gray-600 mb-1">Qualité</div>
                <div className="flex items-center space-x-2">
                  <div className="flex-1 bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${
                        kpi.quality_score >= 90 ? 'bg-green-500' :
                        kpi.quality_score >= 75 ? 'bg-yellow-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${kpi.quality_score}%` }}
                    ></div>
                  </div>
                  <span className="text-sm font-bold text-gray-900">{kpi.quality_score}</span>
                </div>
              </div>

              {/* Safety */}
              <div className="bg-gray-50 p-3 rounded">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-gray-600">Incidents</span>
                  {kpi.safety_incidents === 0 ? (
                    <CheckCircle className="w-4 h-4 text-green-500" />
                  ) : (
                    <XCircle className="w-4 h-4 text-red-500" />
                  )}
                </div>
                <div className={`text-lg font-bold ${
                  kpi.safety_incidents === 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {kpi.safety_incidents}
                </div>
              </div>

              {/* Satisfaction */}
              <div className="bg-gray-50 p-3 rounded">
                <div className="text-xs text-gray-600 mb-1">Satisfaction</div>
                <div className="flex items-center space-x-1">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <svg
                      key={star}
                      className={`w-4 h-4 ${
                        star <= kpi.client_satisfaction_score ? 'text-yellow-400' : 'text-gray-300'
                      }`}
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                    </svg>
                  ))}
                </div>
              </div>

              {/* CPI */}
              <div className="bg-gray-50 p-3 rounded">
                <div className="text-xs text-gray-600 mb-1">CPI</div>
                <div className={`text-lg font-bold ${
                  kpi.cost_performance_index >= 1 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {kpi.cost_performance_index?.toFixed(2) || 'N/A'}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default KPIs;