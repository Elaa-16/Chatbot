import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { Building2, Eye, X, FolderKanban } from 'lucide-react';
import api from '../services/api';

const Clients = () => {
  const { user } = useAuth();
  const [clients, setClients] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedClient, setSelectedClient] = useState(null);
  const [clientProjects, setClientProjects] = useState([]);
  const [showDetailsModal, setShowDetailsModal] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const response = await api.get('/projects');
      const projectsData = response.data;
      setProjects(projectsData);
      
      // Extraire les clients uniques des projets
      const uniqueClients = {};
      projectsData.forEach(project => {
        if (project.client_name && !uniqueClients[project.client_name]) {
          uniqueClients[project.client_name] = {
            client_name: project.client_name,
            total_projects: 0,
            total_budget: 0,
            total_actual_cost: 0,
            active_projects: 0,
            completed_projects: 0
          };
        }
        
        if (project.client_name) {
          uniqueClients[project.client_name].total_projects++;
          uniqueClients[project.client_name].total_budget += project.budget_eur || 0;
          uniqueClients[project.client_name].total_actual_cost += project.actual_cost_eur || 0;
          
          if (project.status === 'In Progress' || project.status === 'Planning') {
            uniqueClients[project.client_name].active_projects++;
          }
          if (project.status === 'Completed') {
            uniqueClients[project.client_name].completed_projects++;
          }
        }
      });
      
      setClients(Object.values(uniqueClients));
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetails = (client) => {
    setSelectedClient(client);
    
    // Filtrer les projets de ce client
    const filteredProjects = projects.filter(p => p.client_name === client.client_name);
    setClientProjects(filteredProjects);
    setShowDetailsModal(true);
  };

  const getClientType = (clientName) => {
    // Déterminer le type de client basé sur le nom
    if (clientName.includes('Ministère') || clientName.includes('Municipalité') || clientName.includes('Gouvernorat')) {
      return { type: 'Gouvernement', color: 'bg-purple-100 text-purple-800' };
    } else if (clientName.includes('ONAS') || clientName.includes('UNESCO')) {
      return { type: 'Public', color: 'bg-blue-100 text-blue-800' };
    } else if (clientName.includes('Société') || clientName.includes('SA') || clientName.includes('Group')) {
      return { type: 'Privé', color: 'bg-green-100 text-green-800' };
    } else {
      return { type: 'Particulier', color: 'bg-yellow-100 text-yellow-800' };
    }
  };

  if (loading) {
    return <div className="text-center py-8">Chargement...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Clients</h1>
          <p className="text-gray-600 mt-1">{clients.length} client(s)</p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">Total Clients</div>
          <div className="text-2xl font-bold text-indigo-600 mt-1">{clients.length}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">Projets Actifs</div>
          <div className="text-2xl font-bold text-green-600 mt-1">
            {clients.reduce((sum, c) => sum + c.active_projects, 0)}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">Projets Terminés</div>
          <div className="text-2xl font-bold text-blue-600 mt-1">
            {clients.reduce((sum, c) => sum + c.completed_projects, 0)}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">Budget Total</div>
          <div className="text-2xl font-bold text-purple-600 mt-1">
            {(clients.reduce((sum, c) => sum + c.total_budget, 0) / 1000000).toFixed(1)}M €
          </div>
        </div>
      </div>

      {/* Clients Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {clients.map((client, index) => {
          const clientType = getClientType(client.client_name);
          const budgetUsage = ((client.total_actual_cost / client.total_budget) * 100).toFixed(1);
          
          return (
            <div key={index} className="bg-white rounded-lg shadow hover:shadow-lg transition p-6">
              <div className="flex justify-between items-start mb-4">
                <div className="flex-1">
                  <h3 className="text-lg font-bold text-gray-900 mb-2">{client.client_name}</h3>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${clientType.color}`}>
                    {clientType.type}
                  </span>
                </div>
              </div>

              <div className="space-y-3 mb-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Projets</span>
                  <span className="font-semibold text-gray-900">{client.total_projects}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">En cours</span>
                  <span className="font-semibold text-green-600">{client.active_projects}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Terminés</span>
                  <span className="font-semibold text-blue-600">{client.completed_projects}</span>
                </div>
              </div>

              {/* Financial Info */}
              <div className="border-t pt-4 mb-4">
                <div className="space-y-2">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-600">Budget total</span>
                      <span className="font-semibold text-indigo-600">
                        {(client.total_budget / 1000000).toFixed(2)}M €
                      </span>
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-600">Dépensé</span>
                      <span className="font-semibold text-orange-600">
                        {(client.total_actual_cost / 1000000).toFixed(2)}M €
                      </span>
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-600 mb-1">Utilisation budget</div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full transition-all ${
                          budgetUsage > 100 ? 'bg-red-500' : 'bg-green-500'
                        }`}
                        style={{ width: `${Math.min(budgetUsage, 100)}%` }}
                      ></div>
                    </div>
                    <div className="text-xs text-right mt-1 font-medium">{budgetUsage}%</div>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <button
                onClick={() => handleViewDetails(client)}
                className="w-full flex items-center justify-center space-x-2 bg-indigo-50 text-indigo-600 px-4 py-2 rounded hover:bg-indigo-100 transition"
              >
                <Eye className="w-4 h-4" />
                <span>Voir les projets</span>
              </button>
            </div>
          );
        })}
      </div>

      {clients.length === 0 && (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <Building2 className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-600">Aucun client trouvé</p>
        </div>
      )}

      {/* Details Modal */}
      {showDetailsModal && selectedClient && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <div>
                  <h2 className="text-2xl font-bold">{selectedClient.client_name}</h2>
                  <div className="flex items-center space-x-4 mt-2 text-sm text-gray-600">
                    <span>{selectedClient.total_projects} projet(s)</span>
                    <span>•</span>
                    <span className="text-green-600">{selectedClient.active_projects} en cours</span>
                    <span>•</span>
                    <span className="text-blue-600">{selectedClient.completed_projects} terminé(s)</span>
                  </div>
                </div>
                <button 
                  onClick={() => setShowDetailsModal(false)} 
                  className="text-gray-500 hover:text-gray-700"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              {/* Financial Summary */}
              <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg p-6 mb-6">
                <h3 className="font-semibold mb-4">Résumé Financier</h3>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <div className="text-sm text-gray-600">Budget Total</div>
                    <div className="text-2xl font-bold text-indigo-600">
                      {(selectedClient.total_budget / 1000000).toFixed(2)}M €
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600">Dépensé</div>
                    <div className="text-2xl font-bold text-orange-600">
                      {(selectedClient.total_actual_cost / 1000000).toFixed(2)}M €
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600">Restant</div>
                    <div className="text-2xl font-bold text-green-600">
                      {((selectedClient.total_budget - selectedClient.total_actual_cost) / 1000000).toFixed(2)}M €
                    </div>
                  </div>
                </div>
              </div>

              {/* Projects List */}
              <div>
                <h3 className="font-semibold mb-4 flex items-center">
                  <FolderKanban className="w-5 h-5 mr-2" />
                  Projets ({clientProjects.length})
                </h3>
                <div className="space-y-3">
                  {clientProjects.map((project) => (
                    <div key={project.project_id} className="border rounded-lg p-4 hover:bg-gray-50 transition">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex-1">
                          <div className="font-medium text-gray-900">{project.project_name}</div>
                          <div className="text-sm text-gray-600">{project.project_type} • {project.location}</div>
                        </div>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          project.status === 'Completed' ? 'bg-green-100 text-green-800' :
                          project.status === 'In Progress' ? 'bg-blue-100 text-blue-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {project.status}
                        </span>
                      </div>
                      
                      <div className="grid grid-cols-3 gap-4 mt-3 text-sm">
                        <div>
                          <div className="text-gray-600">Budget</div>
                          <div className="font-semibold">{project.budget_eur?.toLocaleString()} €</div>
                        </div>
                        <div>
                          <div className="text-gray-600">Dépensé</div>
                          <div className="font-semibold">{project.actual_cost_eur?.toLocaleString()} €</div>
                        </div>
                        <div>
                          <div className="text-gray-600">Avancement</div>
                          <div className="font-semibold text-indigo-600">{project.completion_percentage}%</div>
                        </div>
                      </div>

                      {/* Progress Bar */}
                      <div className="mt-3">
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-indigo-600 h-2 rounded-full transition-all"
                            style={{ width: `${project.completion_percentage}%` }}
                          ></div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Clients;