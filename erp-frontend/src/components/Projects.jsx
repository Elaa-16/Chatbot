import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { getProjects, createProject, updateProject, deleteProject, getEmployees } from '../services/api';
import { Plus, Edit, Trash2, X, UserPlus } from 'lucide-react';

const Projects = () => {
  const { user, isCEO, isManager } = useAuth();
  const [projects, setProjects] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingProject, setEditingProject] = useState(null);
  const [formData, setFormData] = useState({});
  const [selectedEmployees, setSelectedEmployees] = useState([]);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [projectsRes, employeesRes] = await Promise.all([getProjects(), getEmployees()]);
      setProjects(projectsRes.data);
      setEmployees(employeesRes.data);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingProject(null);
    setFormData({
      project_id: '', project_name: '', project_type: '', client_name: '',
      start_date: '', end_date: '', status: 'Planning', budget_eur: '',
      actual_cost_eur: 0, completion_percentage: 0, location: '',
      project_manager_id: '', site_supervisor_id: '', description: '',
    });
    setSelectedEmployees([]);
    setShowModal(true);
  };

  // ✅ FIX 1: Pre-populate selectedEmployees from existing project data
  const handleEdit = (project) => {
    setEditingProject(project);
    setFormData(project);
    const existing = project.assigned_employees
      ? project.assigned_employees.split(';').filter(Boolean)
      : [];
    setSelectedEmployees(existing);
    setShowModal(true);
  };

  // ✅ FIX 2: Actually build and send assigned_employees — dead code removed
  // ✅ FIX 3: Auto-include project_manager_id and site_supervisor_id in the assigned set
  const handleSubmit = async (e) => {
    e.preventDefault();
    const autoAssigned = [formData.project_manager_id, formData.site_supervisor_id].filter(Boolean);
    const allAssigned = [...new Set([...selectedEmployees, ...autoAssigned])];
    const projectData = {
      ...formData,
      assigned_employees: allAssigned.join(';'),
    };
    try {
      if (editingProject) {
        await updateProject(editingProject.project_id, projectData);
      } else {
        await createProject(projectData);
      }
      setShowModal(false);
      loadData();
    } catch (error) {
      console.error('Error saving project:', error);
      alert(error.response?.data?.detail || 'Erreur lors de la sauvegarde');
    }
  };

  const handleDelete = async (projectId) => {
    if (!window.confirm('Êtes-vous sûr de vouloir supprimer ce projet ?')) return;
    try {
      await deleteProject(projectId);
      loadData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Erreur lors de la suppression');
    }
  };

  const toggleEmployeeSelection = (employeeId) => {
    setSelectedEmployees(prev =>
      prev.includes(employeeId) ? prev.filter(id => id !== employeeId) : [...prev, employeeId]
    );
  };

  const getStatusColor = (status) => {
    const colors = {
      'Planning': 'bg-gray-100 text-gray-800', 'In Progress': 'bg-blue-100 text-blue-800',
      'Completed': 'bg-green-100 text-green-800', 'On Hold': 'bg-yellow-100 text-yellow-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  if (loading) return <div className="text-center py-8">Chargement...</div>;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Projets</h1>
          <p className="text-gray-600 mt-1">{projects.length} projet(s) accessible(s)</p>
        </div>
        {(isCEO || isManager) && (
          <button onClick={handleCreate}
            className="flex items-center space-x-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition">
            <Plus className="w-5 h-5" /><span>Nouveau Projet</span>
          </button>
        )}
      </div>

      {/* Projects Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {projects.map((project) => (
          <div key={project.project_id} className="bg-white rounded-lg shadow hover:shadow-lg transition p-6">
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-lg font-bold text-gray-900">{project.project_name}</h3>
              <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(project.status)}`}>
                {project.status}
              </span>
            </div>
            <div className="space-y-2 text-sm text-gray-600">
              <div><span className="font-medium">ID:</span> {project.project_id}</div>
              <div><span className="font-medium">Type:</span> {project.project_type}</div>
              <div><span className="font-medium">Client:</span> {project.client_name}</div>
              <div><span className="font-medium">Lieu:</span> {project.location}</div>
              <div><span className="font-medium">Budget:</span> {project.budget_eur?.toLocaleString()} €</div>
            </div>
            <div className="mt-4">
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-600">Avancement</span>
                <span className="font-medium text-indigo-600">{project.completion_percentage}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-indigo-600 h-2 rounded-full transition-all"
                  style={{ width: `${project.completion_percentage}%` }}></div>
              </div>
            </div>
            {(isCEO || isManager) && (
              <div className="flex space-x-2 mt-4">
                <button onClick={() => handleEdit(project)}
                  className="flex-1 flex items-center justify-center space-x-1 bg-blue-50 text-blue-600 px-3 py-2 rounded hover:bg-blue-100 transition">
                  <Edit className="w-4 h-4" /><span>Modifier</span>
                </button>
                <button onClick={() => handleDelete(project.project_id)}
                  className="flex-1 flex items-center justify-center space-x-1 bg-red-50 text-red-600 px-3 py-2 rounded hover:bg-red-100 transition">
                  <Trash2 className="w-4 h-4" /><span>Supprimer</span>
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold">
                  {editingProject ? 'Modifier le Projet' : 'Nouveau Projet'}
                </h2>
                <button onClick={() => setShowModal(false)} className="text-gray-500 hover:text-gray-700">
                  <X className="w-6 h-6" />
                </button>
              </div>

              <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold mb-3 flex items-center">
                    <span className="bg-indigo-100 text-indigo-800 px-2 py-1 rounded mr-2">1</span>
                    Informations du Projet
                  </h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">ID Projet *</label>
                      <input type="text" value={formData.project_id || ''}
                        onChange={(e) => setFormData({ ...formData, project_id: e.target.value })}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
                        required disabled={!!editingProject} />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Nom du Projet *</label>
                      <input type="text" value={formData.project_name || ''}
                        onChange={(e) => setFormData({ ...formData, project_name: e.target.value })}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500" required />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
                      <select value={formData.project_type || ''}
                        onChange={(e) => setFormData({ ...formData, project_type: e.target.value })}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500">
                        <option value="">Sélectionner...</option>
                        <option value="Residential">Résidentiel</option>
                        <option value="Commercial">Commercial</option>
                        <option value="Industrial">Industriel</option>
                        <option value="Infrastructure">Infrastructure</option>
                        <option value="Healthcare">Santé</option>
                        <option value="Education">Éducation</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Client</label>
                      <input type="text" value={formData.client_name || ''}
                        onChange={(e) => setFormData({ ...formData, client_name: e.target.value })}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Date de Début</label>
                      <input type="date" value={formData.start_date || ''}
                        onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Date de Fin</label>
                      <input type="date" value={formData.end_date || ''}
                        onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Statut</label>
                      <select value={formData.status || 'Planning'}
                        onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500">
                        <option value="Planning">Planning</option>
                        <option value="In Progress">In Progress</option>
                        <option value="Completed">Completed</option>
                        <option value="On Hold">On Hold</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Lieu</label>
                      <input type="text" value={formData.location || ''}
                        onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Budget (€)</label>
                      <input type="number" value={formData.budget_eur || ''}
                        onChange={(e) => setFormData({ ...formData, budget_eur: parseFloat(e.target.value) })}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Coût Actuel (€)</label>
                      <input type="number" value={formData.actual_cost_eur || 0}
                        onChange={(e) => setFormData({ ...formData, actual_cost_eur: parseFloat(e.target.value) })}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Avancement (%)</label>
                      <input type="number" min="0" max="100" value={formData.completion_percentage || 0}
                        onChange={(e) => setFormData({ ...formData, completion_percentage: parseInt(e.target.value) })}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Chef de Projet</label>
                      <select value={formData.project_manager_id || ''}
                        onChange={(e) => setFormData({ ...formData, project_manager_id: e.target.value })}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500">
                        <option value="">Sélectionner...</option>
                        {employees.filter(e => e.role === 'manager' || e.role === 'ceo').map(emp => (
                          <option key={emp.employee_id} value={emp.employee_id}>
                            {emp.first_name} {emp.last_name} ({emp.position})
                          </option>
                        ))}
                      </select>
                    </div>
                    {/* ✅ FIX 4: site_supervisor_id field — was completely missing from the form */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Chef de Chantier</label>
                      <select value={formData.site_supervisor_id || ''}
                        onChange={(e) => setFormData({ ...formData, site_supervisor_id: e.target.value })}
                        className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500">
                        <option value="">Sélectionner...</option>
                        {employees.filter(e => e.role === 'employee' || e.role === 'manager').map(emp => (
                          <option key={emp.employee_id} value={emp.employee_id}>
                            {emp.first_name} {emp.last_name} ({emp.position})
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                    <textarea value={formData.description || ''}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500" rows="3" />
                  </div>
                </div>

                {/* Employee Assignment */}
                <div>
                  <h3 className="text-lg font-semibold mb-3 flex items-center">
                    <span className="bg-indigo-100 text-indigo-800 px-2 py-1 rounded mr-2">2</span>
                    <UserPlus className="w-5 h-5 mr-2" />
                    Assigner des Employés
                  </h3>
                  <p className="text-sm text-gray-600 mb-3">
                    Sélectionnez les employés qui travailleront sur ce projet.
                    Le chef de projet et chef de chantier sont inclus automatiquement.
                  </p>
                  <div className="border rounded-lg p-4 max-h-64 overflow-y-auto">
                    <div className="grid grid-cols-2 gap-3">
                      {employees.filter(e => e.role === 'employee' || e.role === 'manager').map((employee) => (
                        <label key={employee.employee_id}
                          className={`flex items-center p-3 border rounded-lg cursor-pointer transition ${
                            selectedEmployees.includes(employee.employee_id)
                              ? 'bg-indigo-50 border-indigo-500' : 'hover:bg-gray-50'
                          }`}>
                          <input type="checkbox"
                            checked={selectedEmployees.includes(employee.employee_id)}
                            onChange={() => toggleEmployeeSelection(employee.employee_id)}
                            className="mr-3" />
                          <div className="flex-1">
                            <div className="font-medium text-sm">{employee.first_name} {employee.last_name}</div>
                            <div className="text-xs text-gray-600">{employee.position}</div>
                          </div>
                          <span className={`px-2 py-1 rounded text-xs ${
                            employee.role === 'manager' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'
                          }`}>
                            {employee.role === 'manager' ? 'Manager' : 'Employé'}
                          </span>
                        </label>
                      ))}
                    </div>
                  </div>
                  {selectedEmployees.length > 0 && (
                    <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded">
                      <p className="text-sm text-green-800">
                        ✓ {selectedEmployees.length} employé(s) sélectionné(s)
                        {(formData.project_manager_id || formData.site_supervisor_id) && (
                          <span className="text-gray-600"> + chef(s) inclus automatiquement</span>
                        )}
                      </p>
                    </div>
                  )}
                </div>

                <div className="flex space-x-3 pt-4 border-t">
                  <button type="submit"
                    className="flex-1 bg-indigo-600 text-white py-3 rounded-lg hover:bg-indigo-700 transition font-medium">
                    {editingProject ? 'Mettre à jour' : 'Créer le Projet'}
                  </button>
                  <button type="button" onClick={() => setShowModal(false)}
                    className="flex-1 bg-gray-200 text-gray-800 py-3 rounded-lg hover:bg-gray-300 transition font-medium">
                    Annuler
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Projects;