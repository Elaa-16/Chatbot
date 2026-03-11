import React, { useState, useEffect } from 'react';
import { 
  PlusCircle, 
  Edit2, 
  Trash2, 
  CheckCircle, 
  Clock, 
  AlertCircle,
  Search
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import './Tasks.css';

const Tasks = () => {
  const { user } = useAuth();
  const [tasks, setTasks] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [editingTask, setEditingTask] = useState(null);
  const [filters, setFilters] = useState({
    project_id: '',
    status: '',
    priority: '',
    assigned_to: ''
  });
  const [searchTerm, setSearchTerm] = useState('');

  const [formData, setFormData] = useState({
    task_id: '',
    project_id: '',
    assigned_to: '',
    title: '',
    description: '',
    priority: 'Medium',
    status: 'Todo',
    due_date: '',
    estimated_hours: ''
  });

  // ── Rôles ────────────────────────────────────────────────────────────────
  const isEmployee = user?.role === 'employee';
  const isManager  = user?.role === 'manager';   // ← FIX : scope manager

  const getAuthHeaders = () => ({
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${localStorage.getItem('token')}`
  });

  // ============================================================================
  // CHARGEMENT DES DONNÉES
  // ============================================================================

  useEffect(() => {
    if (user) {
      fetchTasks();
      fetchEmployees();
      fetchProjects();
    }
  }, [filters, user]);

  const fetchTasks = async () => {
    try {
      setLoading(true);

      const activeFilters = { ...filters };

      // ✅ Employee : uniquement ses propres tâches
      if (isEmployee) {
        activeFilters.assigned_to = user.employee_id;
      }

      // ✅ FIX — Manager : uniquement les tâches de son équipe
      // Le backend interprète supervised_by comme un filtre virtuel
      // et renvoie les tâches des employés supervisés par ce manager.
      if (isManager) {
        activeFilters.supervised_by = user.employee_id;
      }

      const queryParams = new URLSearchParams(
        Object.entries(activeFilters).filter(([_, value]) => value !== '')
      ).toString();

      const response = await fetch(
        `http://localhost:8000/tasks${queryParams ? '?' + queryParams : ''}`,
        { headers: getAuthHeaders() }
      );

      if (!response.ok) {
        if (response.status === 401) throw new Error('Non autorisé. Veuillez vous reconnecter.');
        throw new Error('Erreur lors du chargement des tâches');
      }

      const data = await response.json();
      setTasks(data);
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching tasks:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchEmployees = async () => {
    try {
      // ✅ FIX — Manager ne voit que les employés de son équipe
      const url = isManager
        ? `http://localhost:8000/employees?supervised_by=${user.employee_id}`
        : 'http://localhost:8000/employees';

      const response = await fetch(url, { headers: getAuthHeaders() });
      if (response.ok) {
        const data = await response.json();
        setEmployees(data);
      }
    } catch (err) {
      console.error('Error fetching employees:', err);
    }
  };

  const fetchProjects = async () => {
    try {
      const response = await fetch('http://localhost:8000/projects', {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        setProjects(data);
      }
    } catch (err) {
      console.error('Error fetching projects:', err);
    }
  };

  // ============================================================================
  // ACTIONS SUR LES TÂCHES
  // ============================================================================

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const url = editingTask
        ? `http://localhost:8000/tasks/${editingTask.task_id}`
        : 'http://localhost:8000/tasks';

      const method = editingTask ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: getAuthHeaders(),
        body: JSON.stringify({
          ...formData,
          created_by: user?.employee_id || 'E001',
          estimated_hours: parseFloat(formData.estimated_hours) || 0
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Erreur lors de la sauvegarde');
      }

      fetchTasks();
      handleCloseModal();
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('Error saving task:', err);
    }
  };

  const handleDelete = async (taskId) => {
    if (!window.confirm('Êtes-vous sûr de vouloir supprimer cette tâche ?')) return;
    try {
      const response = await fetch(`http://localhost:8000/tasks/${taskId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });
      if (!response.ok) throw new Error('Erreur lors de la suppression');
      fetchTasks();
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleStatusChange = async (taskId, newStatus) => {
    try {
      const response = await fetch(
        `http://localhost:8000/tasks/${taskId}/status?new_status=${newStatus}`,
        { method: 'PUT', headers: getAuthHeaders() }
      );
      if (!response.ok) throw new Error('Erreur lors du changement de statut');
      fetchTasks();
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleEdit = (task) => {
    setEditingTask(task);
    setFormData({
      task_id: task.task_id,
      project_id: task.project_id,
      assigned_to: task.assigned_to,
      title: task.title,
      description: task.description || '',
      priority: task.priority,
      status: task.status,
      due_date: task.due_date || '',
      estimated_hours: task.estimated_hours || ''
    });
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setEditingTask(null);
    setFormData({
      task_id: '',
      project_id: '',
      assigned_to: '',
      title: '',
      description: '',
      priority: 'Medium',
      status: 'Todo',
      due_date: '',
      estimated_hours: ''
    });
  };

  // ============================================================================
  // HELPERS
  // ============================================================================

  const getPriorityColor = (priority) => {
    const colors = {
      'Critical': 'priority-critical',
      'High': 'priority-high',
      'Medium': 'priority-medium',
      'Low': 'priority-low'
    };
    return colors[priority] || 'priority-medium';
  };

  const getStatusIcon = (status) => {
    const icons = {
      'Todo': <Clock size={16} />,
      'In Progress': <AlertCircle size={16} />,
      'Done': <CheckCircle size={16} />,
      'Blocked': <AlertCircle size={16} />
    };
    return icons[status] || <Clock size={16} />;
  };

  const getEmployeeName = (employeeId) => {
    const employee = employees.find(emp => emp.employee_id === employeeId);
    return employee ? `${employee.first_name} ${employee.last_name}` : employeeId;
  };

  const getProjectName = (projectId) => {
    const project = projects.find(proj => proj.project_id === projectId);
    return project ? project.project_name : projectId;
  };

  const filteredTasks = tasks.filter(task =>
    task.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    task.description?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const groupedTasks = {
    'Todo': filteredTasks.filter(t => t.status === 'Todo'),
    'In Progress': filteredTasks.filter(t => t.status === 'In Progress'),
    'Done': filteredTasks.filter(t => t.status === 'Done'),
    'Blocked': filteredTasks.filter(t => t.status === 'Blocked')
  };

  if (loading) return <div className="loading">Chargement des tâches...</div>;

  return (
    <div className="tasks-container">
      {error && (
        <div className="error-banner">
          ⚠️ {error}
          <button onClick={() => setError(null)}>✕</button>
        </div>
      )}

      <div className="tasks-header">
        <h1>Gestion des Tâches</h1>
        {/* ✅ Only CEO/Manager can create tasks */}
        {!isEmployee && (
          <button className="btn-primary" onClick={() => setShowModal(true)}>
            <PlusCircle size={20} />
            Nouvelle Tâche
          </button>
        )}
      </div>

      {/* Filters and Search */}
      <div className="tasks-controls">
        <div className="search-box">
          <Search size={20} />
          <input
            type="text"
            placeholder="Rechercher une tâche..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="filters">
          <select
            value={filters.priority}
            onChange={(e) => setFilters({...filters, priority: e.target.value})}
          >
            <option value="">Toutes les priorités</option>
            <option value="Critical">Critique</option>
            <option value="High">Haute</option>
            <option value="Medium">Moyenne</option>
            <option value="Low">Basse</option>
          </select>

          <select
            value={filters.project_id}
            onChange={(e) => setFilters({...filters, project_id: e.target.value})}
          >
            <option value="">Tous les projets</option>
            {projects.map(project => (
              <option key={project.project_id} value={project.project_id}>
                {project.project_id} - {project.project_name}
              </option>
            ))}
          </select>

          {/* ✅ Hide employee filter from employees
              ✅ FIX — Manager voit seulement les employés de son équipe (déjà filtré via fetchEmployees) */}
          {!isEmployee && (
            <select
              value={filters.assigned_to}
              onChange={(e) => setFilters({...filters, assigned_to: e.target.value})}
            >
              <option value="">
                {isManager ? 'Toute mon équipe' : 'Tous les employés'}
              </option>
              {employees.map(emp => (
                <option key={emp.employee_id} value={emp.employee_id}>
                  {emp.first_name} {emp.last_name}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      {/* Kanban Board */}
      <div className="kanban-board">
        {Object.entries(groupedTasks).map(([status, statusTasks]) => (
          <div key={status} className="kanban-column">
            <div className="column-header">
              <h3>
                {getStatusIcon(status)}
                {status}
                <span className="task-count">{statusTasks.length}</span>
              </h3>
            </div>

            <div className="task-list">
              {statusTasks.map(task => (
                <div key={task.task_id} className={`task-card ${getPriorityColor(task.priority)}`}>
                  <div className="task-header">
                    <span className="task-id">{task.task_id}</span>
                    {/* ✅ Only CEO/Manager can edit or delete */}
                    {!isEmployee && (
                      <div className="task-actions">
                        <button onClick={() => handleEdit(task)} title="Modifier">
                          <Edit2 size={16} />
                        </button>
                        <button onClick={() => handleDelete(task.task_id)} title="Supprimer">
                          <Trash2 size={16} />
                        </button>
                      </div>
                    )}
                  </div>

                  <h4>{task.title}</h4>
                  {task.description && (
                    <p className="task-description">{task.description}</p>
                  )}

                  <div className="task-meta">
                    <span className="badge badge-priority">{task.priority}</span>
                    <span className="badge badge-project">{task.project_id}</span>
                  </div>

                  <div className="task-footer">
                    <span className="assigned-to">
                      👤 {getEmployeeName(task.assigned_to)}
                    </span>
                    {task.due_date && (
                      <span className="due-date">
                        📅 {new Date(task.due_date).toLocaleDateString('fr-FR')}
                      </span>
                    )}
                  </div>

                  <div className="task-progress">
                    {task.estimated_hours && (
                      <span>⏱️ {task.actual_hours || 0}h / {task.estimated_hours}h</span>
                    )}
                  </div>

                  {/* ✅ Status buttons — employees limited to their own tasks (scope enforced above) */}
                  <div className="status-buttons">
                    {status !== 'Todo' && (
                      <button onClick={() => handleStatusChange(task.task_id, 'Todo')}>
                        ← Todo
                      </button>
                    )}
                    {status !== 'In Progress' && (
                      <button onClick={() => handleStatusChange(task.task_id, 'In Progress')}>
                        🔄 En cours
                      </button>
                    )}
                    {status !== 'Done' && (
                      <button onClick={() => handleStatusChange(task.task_id, 'Done')}>
                        ✓ Terminé
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Modal — only for CEO/Manager */}
      {showModal && !isEmployee && (
        <div className="modal-overlay" onClick={handleCloseModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>{editingTask ? 'Modifier la tâche' : 'Nouvelle tâche'}</h2>

            <form onSubmit={handleSubmit}>
              {!editingTask && (
                <div className="form-group">
                  <label>ID de la tâche *</label>
                  <input
                    type="text"
                    value={formData.task_id}
                    onChange={(e) => setFormData({...formData, task_id: e.target.value})}
                    placeholder="Ex: T010"
                    required
                  />
                </div>
              )}

              <div className="form-row">
                <div className="form-group">
                  <label>Projet *</label>
                  <select
                    value={formData.project_id}
                    onChange={(e) => setFormData({...formData, project_id: e.target.value})}
                    required
                  >
                    <option value="">Sélectionner un projet...</option>
                    {projects.map(project => (
                      <option key={project.project_id} value={project.project_id}>
                        {project.project_id} - {project.project_name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Assigné à *</label>
                  <select
                    value={formData.assigned_to}
                    onChange={(e) => setFormData({...formData, assigned_to: e.target.value})}
                    required
                  >
                    <option value="">Sélectionner un employé...</option>
                    {employees.map(emp => (
                      <option key={emp.employee_id} value={emp.employee_id}>
                        {emp.employee_id} - {emp.first_name} {emp.last_name} ({emp.position})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label>Titre *</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({...formData, title: e.target.value})}
                  placeholder="Ex: Réviser les plans architecturaux"
                  required
                />
              </div>

              <div className="form-group">
                <label>Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                  rows="3"
                  placeholder="Description détaillée de la tâche..."
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Priorité *</label>
                  <select
                    value={formData.priority}
                    onChange={(e) => setFormData({...formData, priority: e.target.value})}
                    required
                  >
                    <option value="Low">Basse</option>
                    <option value="Medium">Moyenne</option>
                    <option value="High">Haute</option>
                    <option value="Critical">Critique</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Statut *</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({...formData, status: e.target.value})}
                    required
                  >
                    <option value="Todo">À faire</option>
                    <option value="In Progress">En cours</option>
                    <option value="Done">Terminé</option>
                    <option value="Blocked">Bloqué</option>
                  </select>
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Date d'échéance</label>
                  <input
                    type="date"
                    value={formData.due_date}
                    onChange={(e) => setFormData({...formData, due_date: e.target.value})}
                  />
                </div>

                <div className="form-group">
                  <label>Heures estimées</label>
                  <input
                    type="number"
                    step="0.5"
                    value={formData.estimated_hours}
                    onChange={(e) => setFormData({...formData, estimated_hours: e.target.value})}
                    placeholder="Ex: 8"
                  />
                </div>
              </div>

              <div className="modal-buttons">
                <button type="button" onClick={handleCloseModal} className="btn-secondary">
                  Annuler
                </button>
                <button type="submit" className="btn-primary">
                  {editingTask ? 'Mettre à jour' : 'Créer'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Tasks;