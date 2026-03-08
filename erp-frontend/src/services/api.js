import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

// ─── Axios Instance ───────────────────────────────────────────────────────────
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// ─── Request Interceptor ─────────────────────────────────────────────────────
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
      return config;
    }
    const auth = localStorage.getItem('auth');
    if (auth) {
      try {
        const { username, password } = JSON.parse(auth);
        config.auth = { username, password };
      } catch {
        localStorage.removeItem('auth');
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ─── Response Interceptor ────────────────────────────────────────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      ['token', 'auth', 'user', 'access_token', 'user_role', 'user_id', 'user_name']
        .forEach(k => localStorage.removeItem(k));
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// ─── Auth ─────────────────────────────────────────────────────────────────────
export const login = async (username, password) => {
  // Plain axios (no interceptor) to avoid auth loop on login failure
  const response = await axios.post(`${API_BASE_URL}/login`, { username, password });
  const { access_token, user } = response.data;

  if (!access_token) throw new Error('Pas de token reçu du serveur');

  // Store full user object — must_change_password is preserved inside
  localStorage.setItem('token',        access_token);
  localStorage.setItem('user',         JSON.stringify(user));
  localStorage.setItem('auth',         JSON.stringify({ username, password }));
  localStorage.setItem('access_token', access_token);
  localStorage.setItem('user_role',    user.role);
  localStorage.setItem('user_id',      user.employee_id);
  localStorage.setItem('user_name',    `${user.first_name} ${user.last_name}`);

  // Return FULL user object so AuthContext receives must_change_password
  return user;
};

export const logout = () => {
  ['token', 'auth', 'user', 'access_token', 'user_role', 'user_id', 'user_name']
    .forEach(k => localStorage.removeItem(k));
};

export const getMe = () => api.get('/me');

// ─── Projects ────────────────────────────────────────────────────────────────
export const getProjects     = ()         => api.get('/projects');
export const getProject      = (id)       => api.get(`/projects/${id}`);
export const createProject   = (data)     => api.post('/projects', data);
export const updateProject   = (id, data) => api.put(`/projects/${id}`, data);
export const deleteProject   = (id)       => api.delete(`/projects/${id}`);

// ─── Tasks ───────────────────────────────────────────────────────────────────
export const getTasks        = ()         => api.get('/tasks');
export const getTask         = (id)       => api.get(`/tasks/${id}`);
export const getProjectTasks = (pid)      => api.get(`/tasks/project/${pid}`);
export const createTask      = (data)     => api.post('/tasks', data);
export const updateTask      = (id, data) => api.put(`/tasks/${id}`, data);
export const deleteTask      = (id)       => api.delete(`/tasks/${id}`);

// ─── Issues / Incidents ──────────────────────────────────────────────────────
export const getIssues        = (params)   => api.get('/issues', { params });
export const getIssue         = (id)       => api.get(`/issues/${id}`);
export const getProjectIssues = (pid)      => api.get(`/issues/project/${pid}`);
export const createIssue      = (data)     => api.post('/issues', data);
export const updateIssue      = (id, data) => api.put(`/issues/${id}`, data);
export const deleteIssue      = (id)       => api.delete(`/issues/${id}`);

// ─── Employees ───────────────────────────────────────────────────────────────
export const getEmployees    = ()         => api.get('/employees');
export const getEmployee     = (id)       => api.get(`/employees/${id}`);
export const createEmployee  = (data)     => api.post('/employees', data);
export const updateEmployee  = (id, data) => api.put(`/employees/${id}`, data);
export const deleteEmployee  = (id)       => api.delete(`/employees/${id}`);

// ─── Clients ─────────────────────────────────────────────────────────────────
export const getClients    = ()         => api.get('/clients');
export const getClient     = (id)       => api.get(`/clients/${id}`);
export const createClient  = (data)     => api.post('/clients', data);
export const updateClient  = (id, data) => api.put(`/clients/${id}`, data);
export const deleteClient  = (id)       => api.delete(`/clients/${id}`);

// ─── KPIs ────────────────────────────────────────────────────────────────────
export const getKPIs        = ()          => api.get('/kpis');
export const getProjectKPIs = (pid)       => api.get(`/kpis/project/${pid}`);
export const createKPI      = (data)      => api.post('/kpis', data);
export const updateKPI      = (id, data)  => api.put(`/kpis/${id}`, data);
export const deleteKPI      = (id)        => api.delete(`/kpis/${id}`);

// ─── Reports ─────────────────────────────────────────────────────────────────
export const getReports     = (type)     => api.get('/reports', { params: type ? { report_type: type } : {} });
export const generateReport = (data)     => api.post('/reports/generate', data);

// ─── Notifications ───────────────────────────────────────────────────────────
export const getNotifications         = ()   => api.get('/notifications');
export const getUnreadNotifications   = ()   => api.get('/notifications/unread');
export const markNotificationRead     = (id) => api.put(`/notifications/${id}/read`);
export const markAllNotificationsRead = ()   => api.put('/notifications/mark-all-read');

// ─── Leave Requests ──────────────────────────────────────────────────────────
export const getLeaves    = ()         => api.get('/leave-requests');
export const getLeave     = (id)       => api.get(`/leave-requests/${id}`);
export const createLeave  = (data)     => api.post('/leave-requests', data);
export const updateLeave  = (id, data) => api.put(`/leave-requests/${id}`, data);
export const deleteLeave  = (id)       => api.delete(`/leave-requests/${id}`);

// ─── Equipment ───────────────────────────────────────────────────────────────
export const getEquipment     = ()         => api.get('/equipment');
export const getEquipmentItem = (id)       => api.get(`/equipment/${id}`);
export const createEquipment  = (data)     => api.post('/equipment', data);
export const updateEquipment  = (id, data) => api.put(`/equipment/${id}`, data);
export const deleteEquipment  = (id)       => api.delete(`/equipment/${id}`);

// ─── Suppliers ───────────────────────────────────────────────────────────────
export const getSuppliers   = ()         => api.get('/suppliers');
export const getSupplier    = (id)       => api.get(`/suppliers/${id}`);
export const createSupplier = (data)     => api.post('/suppliers', data);
export const updateSupplier = (id, data) => api.put(`/suppliers/${id}`, data);
export const deleteSupplier = (id)       => api.delete(`/suppliers/${id}`);

// ─── Purchase Orders ─────────────────────────────────────────────────────────
export const getPurchaseOrders   = ()          => api.get('/purchase-orders');
export const getPurchaseOrder    = (id)        => api.get(`/purchase-orders/${id}`);
export const createPurchaseOrder = (data)      => api.post('/purchase-orders', data);
export const updatePurchaseOrder = (id, data)  => api.put(`/purchase-orders/${id}`, data);
export const deletePurchaseOrder = (id)        => api.delete(`/purchase-orders/${id}`);

// ─── Stats ───────────────────────────────────────────────────────────────────
export const getStats     = () => api.get('/stats/summary');
export const getTaskStats = () => api.get('/stats/tasks');

export default api;