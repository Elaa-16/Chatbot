import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { Calendar, Clock, CheckCircle, XCircle, AlertCircle, Plus, X } from 'lucide-react';
import api from '../services/api';

const LeaveRequests = () => {
  const { user, isCEO, isManager, isRH } = useAuth();
  const [requests, setRequests] = useState([]);
  const [pendingRequests, setPendingRequests] = useState([]);
  const [leaveStats, setLeaveStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [reviewAction, setReviewAction] = useState(null);
  const [selectedRequestForReview, setSelectedRequestForReview] = useState(null);
  const [reviewComment, setReviewComment] = useState('');
  const [filter, setFilter] = useState('all');
  
  const [formData, setFormData] = useState({
    leave_type: 'Annual',
    start_date: '',
    end_date: '',
    reason: ''
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [requestsRes, pendingRes, statsRes] = await Promise.all([
        api.get('/leave-requests'),
        // CEO no longer fetches pending — only RH and managers act on them
        (isManager || isRH) ? api.get('/leave-requests/pending') : Promise.resolve({ data: [] }),
        api.get(`/employees/${user.employee_id}/leave-stats`)
      ]);
      setRequests(requestsRes.data);
      setPendingRequests(pendingRes.data);
      setLeaveStats(statsRes.data);
    } catch (error) {
      console.error('Error loading leave data:', error);
    } finally {
      setLoading(false);
    }
  };

  const calculateDays = (start, end) => {
    const startDate = new Date(start);
    const endDate = new Date(end);
    const diffTime = Math.abs(endDate - startDate);
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const totalDays = calculateDays(formData.start_date, formData.end_date);
    if (totalDays <= 0) {
      alert('La date de fin doit être après la date de début');
      return;
    }
    try {
      const userResponse = await api.get(`/employees/${user.employee_id}`);
      const employeeData = userResponse.data;
      const requestData = {
        request_id: `LR${Date.now()}`,
        employee_id: user.employee_id,
        employee_name: `${employeeData.first_name} ${employeeData.last_name}`,
        leave_type: formData.leave_type,
        start_date: formData.start_date,
        end_date: formData.end_date,
        total_days: totalDays,
        reason: formData.reason
      };
      await api.post('/leave-requests', requestData);
      setShowModal(false);
      setFormData({ leave_type: 'Annual', start_date: '', end_date: '', reason: '' });
      loadData();
    } catch (error) {
      console.error('Error submitting leave request:', error);
      alert(error.response?.data?.detail || 'Erreur lors de la soumission');
    }
  };

  const openReviewModal = (request, action) => {
    setSelectedRequestForReview(request);
    setReviewAction(action);
    setReviewComment('');
    setShowReviewModal(true);
  };

  const handleReviewSubmit = async () => {
    if (reviewAction === 'reject' && !reviewComment.trim()) {
      alert('Vous devez fournir une raison pour le rejet');
      return;
    }
    try {
      if (reviewAction === 'approve') {
        await api.put(`/leave-requests/${selectedRequestForReview.request_id}/approve`, null, {
          params: { review_comment: reviewComment }
        });
      } else {
        await api.put(`/leave-requests/${selectedRequestForReview.request_id}/reject?review_comment=${encodeURIComponent(reviewComment)}`);
      }
      setShowReviewModal(false);
      setReviewComment('');
      setSelectedRequestForReview(null);
      loadData();
    } catch (error) {
      console.error('Error reviewing request:', error);
      alert(error.response?.data?.detail || 'Erreur lors de la révision');
    }
  };

  const handleCancel = async (requestId) => {
    if (!window.confirm('Êtes-vous sûr de vouloir annuler cette demande ?')) return;
    try {
      await api.put(`/leave-requests/${requestId}/cancel`);
      loadData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Erreur lors de l\'annulation');
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      'Pending':   { bg: 'bg-yellow-100', text: 'text-yellow-800', icon: Clock,        label: 'En attente' },
      'Approved':  { bg: 'bg-green-100',  text: 'text-green-800',  icon: CheckCircle,  label: 'Approuvé'   },
      'Rejected':  { bg: 'bg-red-100',    text: 'text-red-800',    icon: XCircle,      label: 'Rejeté'     },
      'Cancelled': { bg: 'bg-gray-100',   text: 'text-gray-800',   icon: AlertCircle,  label: 'Annulé'     },
    };
    const badge = badges[status] || badges.Pending;
    const Icon = badge.icon;
    return (
      <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${badge.bg} ${badge.text}`}>
        <Icon className="w-4 h-4 mr-1" />
        {badge.label}
      </span>
    );
  };

  const getLeaveTypeColor = (type) => {
    const colors = {
      'Annual':    'bg-blue-100 text-blue-800',
      'Sick':      'bg-red-100 text-red-800',
      'Personal':  'bg-purple-100 text-purple-800',
      'Maternity': 'bg-pink-100 text-pink-800',
      'Emergency': 'bg-orange-100 text-orange-800',
    };
    return colors[type] || 'bg-gray-100 text-gray-800';
  };

  const filteredRequests = requests.filter(req => {
    if (filter === 'all') return true;
    return req.status === filter.charAt(0).toUpperCase() + filter.slice(1);
  });

  if (loading) return <div className="text-center py-8">Chargement...</div>;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Gestion des Congés</h1>
          <p className="text-gray-600 mt-1">Demandes et suivi des congés</p>
        </div>
        {/* CEO and RH cannot submit leave requests */}
        {!isCEO && !isRH && (
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center space-x-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition"
          >
            <Plus className="w-5 h-5" />
            <span>Nouvelle Demande</span>
          </button>
        )}
      </div>

      {/* Stats Cards — hide for RH since they don't have personal leave */}
      {!isRH && (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-600">Congés Annuels</div>
            <div className="text-2xl font-bold text-indigo-600 mt-1">{leaveStats?.annual_leave_total || 0}</div>
            <div className="text-xs text-gray-500">Total</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-600">Pris</div>
            <div className="text-2xl font-bold text-orange-600 mt-1">{leaveStats?.annual_leave_taken || 0}</div>
            <div className="text-xs text-gray-500">Jours</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-600">Restants</div>
            <div className="text-2xl font-bold text-green-600 mt-1">{leaveStats?.annual_leave_remaining || 0}</div>
            <div className="text-xs text-gray-500">Jours</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-600">Congés Maladie</div>
            <div className="text-2xl font-bold text-red-600 mt-1">{leaveStats?.sick_leave_taken || 0}</div>
            <div className="text-xs text-gray-500">Jours</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-600">Autres</div>
            <div className="text-2xl font-bold text-purple-600 mt-1">{leaveStats?.other_leave_taken || 0}</div>
            <div className="text-xs text-gray-500">Jours</div>
          </div>
        </div>
      )}

      {/* Pending Approvals banner — only for RH and managers, not CEO */}
      {(isManager || isRH) && pendingRequests.length > 0 && (
        <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded">
          <div className="flex items-start">
            <AlertCircle className="w-5 h-5 text-yellow-500 mt-0.5 mr-3" />
            <div>
              <h3 className="font-medium text-yellow-800">Demandes en attente</h3>
              <p className="text-sm text-yellow-700 mt-1">
                {pendingRequests.length} demande(s) de congé en attente d'approbation
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex space-x-2">
        {['all', 'pending', 'approved', 'rejected'].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 rounded-lg transition ${
              filter === f ? 'bg-indigo-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-50'
            }`}
          >
            {f === 'all' ? 'Toutes' : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {/* Requests List */}
      <div className="space-y-4">
        {filteredRequests.map((request) => (
          <div key={request.request_id} className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-start mb-4">
              <div className="flex-1">
                <div className="flex items-center space-x-3 mb-2">
                  <h3 className="text-lg font-bold text-gray-900">{request.employee_name}</h3>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getLeaveTypeColor(request.leave_type)}`}>
                    {request.leave_type}
                  </span>
                  {getStatusBadge(request.status)}
                </div>
                <div className="flex items-center space-x-4 text-sm text-gray-600">
                  <div className="flex items-center">
                    <Calendar className="w-4 h-4 mr-1" />
                    <span>{request.start_date} → {request.end_date}</span>
                  </div>
                  <div className="font-medium text-indigo-600">{request.total_days} jour(s)</div>
                </div>
                {request.reason && (
                  <div className="mt-2 text-sm text-gray-700">
                    <span className="font-medium">Raison:</span> {request.reason}
                  </div>
                )}
                {request.review_comment && (
                  <div className="mt-2 p-2 bg-gray-50 rounded text-sm">
                    <span className="font-medium">Commentaire:</span> {request.review_comment}
                  </div>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex space-x-2 mt-4 pt-4 border-t">
              {request.status === 'Pending' && (
                <>
                  {/* ✅ Only RH and managers can approve/reject — CEO removed */}
                  {(isRH || (isManager && user.supervised_employees?.includes(request.employee_id))) && (
                    <>
                      <button
                        onClick={() => openReviewModal(request, 'approve')}
                        className="flex items-center space-x-1 bg-green-50 text-green-600 px-4 py-2 rounded hover:bg-green-100 transition"
                      >
                        <CheckCircle className="w-4 h-4" />
                        <span>Approuver</span>
                      </button>
                      <button
                        onClick={() => openReviewModal(request, 'reject')}
                        className="flex items-center space-x-1 bg-red-50 text-red-600 px-4 py-2 rounded hover:bg-red-100 transition"
                      >
                        <XCircle className="w-4 h-4" />
                        <span>Rejeter</span>
                      </button>
                    </>
                  )}
                  {/* Employee can cancel their own request */}
                  {request.employee_id === user.employee_id && (
                    <button
                      onClick={() => handleCancel(request.request_id)}
                      className="flex items-center space-x-1 bg-gray-50 text-gray-600 px-4 py-2 rounded hover:bg-gray-100 transition"
                    >
                      <XCircle className="w-4 h-4" />
                      <span>Annuler</span>
                    </button>
                  )}
                </>
              )}
            </div>
          </div>
        ))}

        {filteredRequests.length === 0 && (
          <div className="text-center py-12 bg-white rounded-lg shadow">
            <Calendar className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-600">Aucune demande de congé trouvée</p>
          </div>
        )}
      </div>

      {/* Create Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-2xl font-bold">Nouvelle Demande de Congé</h2>
              <button onClick={() => setShowModal(false)} className="text-gray-500 hover:text-gray-700">
                <X className="w-6 h-6" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Type de Congé *</label>
                <select
                  value={formData.leave_type}
                  onChange={(e) => setFormData({ ...formData, leave_type: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
                  required
                >
                  <option value="Annual">Congé Annuel</option>
                  <option value="Sick">Congé Maladie</option>
                  <option value="Personal">Congé Personnel</option>
                  <option value="Emergency">Urgence</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Date de Début *</label>
                <input
                  type="date"
                  value={formData.start_date}
                  onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Date de Fin *</label>
                <input
                  type="date"
                  value={formData.end_date}
                  onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
                  required
                />
              </div>
              {formData.start_date && formData.end_date && (
                <div className="p-3 bg-indigo-50 rounded">
                  <p className="text-sm text-indigo-800">
                    <strong>Durée:</strong> {calculateDays(formData.start_date, formData.end_date)} jour(s)
                  </p>
                  {formData.leave_type === 'Annual' && leaveStats && (
                    <p className="text-sm text-indigo-600 mt-1">
                      Restant après: {leaveStats.annual_leave_remaining - calculateDays(formData.start_date, formData.end_date)} jour(s)
                    </p>
                  )}
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Raison</label>
                <textarea
                  value={formData.reason}
                  onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
                  rows="3"
                  placeholder="Optionnel..."
                ></textarea>
              </div>
              <div className="flex space-x-3 pt-4">
                <button type="submit" className="flex-1 bg-indigo-600 text-white py-2 rounded-lg hover:bg-indigo-700 transition">
                  Soumettre
                </button>
                <button type="button" onClick={() => setShowModal(false)} className="flex-1 bg-gray-200 text-gray-800 py-2 rounded-lg hover:bg-gray-300 transition">
                  Annuler
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Review Modal */}
      {showReviewModal && selectedRequestForReview && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-2xl font-bold">
                {reviewAction === 'approve' ? 'Approuver' : 'Rejeter'} la demande
              </h2>
              <button onClick={() => setShowReviewModal(false)} className="text-gray-500 hover:text-gray-700">
                <X className="w-6 h-6" />
              </button>
            </div>
            <div className="mb-4 p-4 bg-gray-50 rounded">
              <p className="text-sm"><strong>Employé:</strong> {selectedRequestForReview.employee_name}</p>
              <p className="text-sm"><strong>Type:</strong> {selectedRequestForReview.leave_type}</p>
              <p className="text-sm"><strong>Période:</strong> {selectedRequestForReview.start_date} → {selectedRequestForReview.end_date}</p>
              <p className="text-sm"><strong>Durée:</strong> {selectedRequestForReview.total_days} jour(s)</p>
            </div>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Commentaire {reviewAction === 'reject' && <span className="text-red-600">*</span>}
              </label>
              <textarea
                value={reviewComment}
                onChange={(e) => setReviewComment(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
                rows="3"
                placeholder={reviewAction === 'approve' ? 'Optionnel...' : 'Raison du rejet (requis)'}
              ></textarea>
            </div>
            <div className="flex space-x-3">
              <button
                onClick={handleReviewSubmit}
                className={`flex-1 text-white py-2 rounded-lg transition ${
                  reviewAction === 'approve' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'
                }`}
              >
                {reviewAction === 'approve' ? 'Approuver' : 'Rejeter'}
              </button>
              <button onClick={() => setShowReviewModal(false)} className="flex-1 bg-gray-200 text-gray-800 py-2 rounded-lg hover:bg-gray-300 transition">
                Annuler
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LeaveRequests;