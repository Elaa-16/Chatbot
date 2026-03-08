import React, { createContext, useState, useContext, useEffect } from 'react';
import { login as apiLogin, logout as apiLogout } from '../services/api';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    const storedUser = localStorage.getItem('user');
    if (token && storedUser) {
      try {
        const parsedUser = JSON.parse(storedUser);
        setUser(parsedUser);
      } catch {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        localStorage.removeItem('auth');
      }
    }
    setLoading(false);
  }, []);

  const login = async (username, password) => {
    try {
      const userData = await apiLogin(username, password);
      setUser(userData);
      return {
        success: true,
        must_change_password: userData.must_change_password
      };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Identifiants invalides'
      };
    }
  };

  const logout = () => {
    apiLogout();
    setUser(null);
  };

  const clearMustChangePassword = () => {
    setUser(prev => {
      const updated = { ...prev, must_change_password: false };
      localStorage.setItem('user', JSON.stringify(updated));
      return updated;
    });
  };

  const value = {
    user,
    login,
    logout,
    loading,
    clearMustChangePassword,
    isAuthenticated: !!user,
    isCEO: user?.role === 'ceo',
    isManager: user?.role === 'manager',
    isEmployee: user?.role === 'employee',
    isRH: user?.role === 'rh',  // ✅ added
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
};