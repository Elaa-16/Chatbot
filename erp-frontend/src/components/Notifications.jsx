import React, { useState, useEffect } from 'react';
import { Bell, CheckCheck, AlertCircle, Info, CheckCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

const Notifications = () => {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all'); // all, unread, read

  useEffect(() => {
    if (user) {
      fetchNotifications();
      
      // Poll for new notifications every 30 seconds
      const interval = setInterval(fetchNotifications, 30000);
      return () => clearInterval(interval);
    }
  }, [filter, user]);

  const fetchNotifications = async () => {
    try {
      setLoading(true);
      const endpoint = filter === 'unread' 
        ? '/notifications/unread'
        : '/notifications';
      
      const response = await api.get(endpoint);
      let data = response.data;
      
      // Filter by read status if needed
      if (filter === 'read') {
        data = data.filter(n => n.is_read);
      }
      
      setNotifications(data);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors du chargement');
      console.error('Error fetching notifications:', err);
    } finally {
      setLoading(false);
    }
  };

  const markAsRead = async (notificationId) => {
    try {
      await api.put(`/notifications/${notificationId}/read`);
      fetchNotifications();
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors du marquage');
      console.error('Error marking as read:', err);
    }
  };

  const markAllAsRead = async () => {
    try {
      await api.put('/notifications/mark-all-read');
      fetchNotifications();
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors du marquage');
      console.error('Error marking all as read:', err);
    }
  };

  const getNotificationIcon = (type, priority) => {
    if (priority === 'Urgent' || priority === 'High') {
      return <AlertCircle size={24} className="text-red-500" />;
    }
    
    switch(type) {
      case 'Task':
        return <CheckCircle size={24} className="text-blue-500" />;
      case 'Alert':
        return <AlertCircle size={24} className="text-orange-500" />;
      case 'System':
        return <Info size={24} className="text-gray-500" />;
      case 'Leave':
        return <Bell size={24} className="text-green-500" />;
      default:
        return <Bell size={24} className="text-indigo-500" />;
    }
  };

  const getPriorityClass = (priority) => {
    const classes = {
      'Urgent': 'border-l-4 border-red-500 bg-red-50',
      'High': 'border-l-4 border-orange-500 bg-orange-50',
      'Medium': 'border-l-4 border-blue-500 bg-blue-50',
      'Low': 'border-l-4 border-gray-300 bg-gray-50'
    };
    return classes[priority] || 'border-l-4 border-gray-300';
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'À l\'instant';
    if (minutes < 60) return `Il y a ${minutes} min`;
    if (hours < 24) return `Il y a ${hours}h`;
    if (days < 7) return `Il y a ${days}j`;
    
    return date.toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'short',
      year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
    });
  };

  const unreadCount = notifications.filter(n => !n.is_read).length;

  if (loading && notifications.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-gray-600">Chargement des notifications...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative">
          ⚠️ {error}
          <button 
            onClick={() => setError(null)}
            className="absolute top-0 bottom-0 right-0 px-4 py-3"
          >
            ✕
          </button>
        </div>
      )}

      <div className="flex justify-between items-center">
        <div className="flex items-center space-x-4">
          <h1 className="text-3xl font-bold text-gray-900 flex items-center">
            <Bell size={28} className="mr-2" />
            Notifications
          </h1>
          {unreadCount > 0 && (
            <span className="bg-red-500 text-white px-3 py-1 rounded-full text-sm font-semibold">
              {unreadCount} non lue{unreadCount > 1 ? 's' : ''}
            </span>
          )}
        </div>
        
        {unreadCount > 0 && (
          <button 
            onClick={markAllAsRead}
            className="flex items-center space-x-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition"
          >
            <CheckCheck size={18} />
            <span>Tout marquer comme lu</span>
          </button>
        )}
      </div>

      <div className="flex space-x-2 border-b">
        <button 
          className={`px-4 py-2 font-medium ${filter === 'all' ? 'border-b-2 border-indigo-600 text-indigo-600' : 'text-gray-600'}`}
          onClick={() => setFilter('all')}
        >
          Toutes ({notifications.length})
        </button>
        <button 
          className={`px-4 py-2 font-medium ${filter === 'unread' ? 'border-b-2 border-indigo-600 text-indigo-600' : 'text-gray-600'}`}
          onClick={() => setFilter('unread')}
        >
          Non lues ({unreadCount})
        </button>
        <button 
          className={`px-4 py-2 font-medium ${filter === 'read' ? 'border-b-2 border-indigo-600 text-indigo-600' : 'text-gray-600'}`}
          onClick={() => setFilter('read')}
        >
          Lues ({notifications.length - unreadCount})
        </button>
      </div>

      <div className="space-y-3">
        {notifications.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg shadow">
            <Bell size={48} className="text-gray-300 mx-auto mb-4" />
            <p className="text-gray-600">Aucune notification</p>
          </div>
        ) : (
          notifications.map(notification => (
            <div 
              key={notification.notification_id}
              className={`bg-white rounded-lg shadow p-4 ${getPriorityClass(notification.priority)} ${!notification.is_read ? 'font-semibold' : ''}`}
            >
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0 mt-1">
                  {getNotificationIcon(notification.type, notification.priority)}
                </div>

                <div className="flex-1">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">
                        {notification.title}
                      </h3>
                      <span className="inline-block px-2 py-1 text-xs font-medium bg-gray-100 text-gray-700 rounded mt-1">
                        {notification.type}
                      </span>
                    </div>
                    <span className="text-sm text-gray-500">
                      {formatDate(notification.created_date)}
                    </span>
                  </div>

                  <p className="text-gray-700 mt-2">
                    {notification.message}
                  </p>

                  {notification.link && (
                    <a 
                      href={notification.link} 
                      className="inline-block mt-2 text-indigo-600 hover:text-indigo-800 text-sm font-medium"
                    >
                      Voir →
                    </a>
                  )}
                </div>

                {!notification.is_read && (
                  <button 
                    onClick={() => markAsRead(notification.notification_id)}
                    className="flex-shrink-0 p-2 text-indigo-600 hover:bg-indigo-50 rounded transition"
                    title="Marquer comme lu"
                  >
                    <CheckCheck size={20} />
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default Notifications;