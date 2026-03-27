import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import Projects from './components/Projects';
import Employees from './components/Employees';
import KPIs from './components/KPIs';
import LeaveRequests from './components/LeaveRequests';
import Clients from './components/Clients';
import Tasks from './components/Tasks';
import Notifications from './components/Notifications';
import Navbar from './components/Navbar';
import Issues from './components/Issues';
import ChangePassword from './components/ChangePassword';
import Reports from './components/Reports';
import ApiWhitelist from './components/ApiWhitelist';
import AuditLogs from './components/AuditLogs';

// ── Redirect based on role after login ────────────────────────────────────────
const getHomePage = (user) => {
  if (!user) return '/login';
  if (user.must_change_password) return '/change-password';
  if (user.role === 'rh') return '/employees';
  return '/dashboard';
};

// ── Protect routes + block rh from non-rh pages ──────────────────────────────
const PrivateRoute = ({ children, allowedRoles }) => {
  const { isAuthenticated, user } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" />;
  if (allowedRoles && !allowedRoles.includes(user?.role)) {
    return <Navigate to={getHomePage(user)} />;
  }
  return children;
};

const SIDEBAR_WIDTH = 260;

const Layout = ({ children }) => (
  <div style={{ minHeight: '100vh', background: '#f3f4f6' }}>
    <Navbar />
    <main style={{
      marginLeft: SIDEBAR_WIDTH,
      padding: '32px',
      minWidth: 0,
      minHeight: '100vh',
      boxSizing: 'border-box',
    }}>
      {children}
    </main>
  </div>
);

function AppRoutes() {
  const { isAuthenticated, user } = useAuth();

  return (
    <Routes>
      {/* Login */}
      <Route
        path="/login"
        element={
          isAuthenticated
            ? <Navigate to={getHomePage(user)} />
            : <Login />
        }
      />

      {/* Change password */}
      <Route path="/change-password" element={<ChangePassword />} />

      {/* Dashboard — not for rh */}
      <Route path="/dashboard" element={
        <PrivateRoute allowedRoles={['ceo', 'manager', 'employee', 'admin']}>
          <Layout><Dashboard /></Layout>
        </PrivateRoute>
      } />

      {/* Projects — not for rh */}
      <Route path="/projects" element={
        <PrivateRoute allowedRoles={['ceo', 'manager', 'employee', 'admin']}>
          <Layout><Projects /></Layout>
        </PrivateRoute>
      } />

      {/* Tasks — not for rh */}
      <Route path="/tasks" element={
        <PrivateRoute allowedRoles={['ceo', 'manager', 'employee', 'admin']}>
          <Layout><Tasks /></Layout>
        </PrivateRoute>
      } />

      {/* Issues — not for rh */}
      <Route path="/issues" element={
        <PrivateRoute allowedRoles={['ceo', 'manager', 'employee', 'admin']}>
          <Layout><Issues /></Layout>
        </PrivateRoute>
      } />

      {/* Reports — ceo and manager only */}
      <Route path="/reports" element={
        <PrivateRoute allowedRoles={['ceo', 'manager', 'admin']}>
          <Layout><Reports /></Layout>
        </PrivateRoute>
      } />

      {/* Clients — ceo and manager only */}
      <Route path="/clients" element={
        <PrivateRoute allowedRoles={['ceo', 'manager', 'admin']}>
          <Layout><Clients /></Layout>
        </PrivateRoute>
      } />

      {/* KPIs — ceo and manager only */}
      <Route path="/kpis" element={
        <PrivateRoute allowedRoles={['ceo', 'manager', 'admin']}>
          <Layout><KPIs /></Layout>
        </PrivateRoute>
      } />

      {/* Employees — all except employee */}
      <Route path="/employees" element={
        <PrivateRoute allowedRoles={['ceo', 'manager', 'rh', 'admin']}>
          <Layout><Employees /></Layout>
        </PrivateRoute>
      } />

      {/* Leave requests — everyone */}
      <Route path="/leave-requests" element={
        <PrivateRoute allowedRoles={['ceo', 'manager', 'employee', 'rh', 'admin']}>
          <Layout><LeaveRequests /></Layout>
        </PrivateRoute>
      } />

      {/* Notifications — everyone */}
      <Route path="/notifications" element={
        <PrivateRoute allowedRoles={['ceo', 'manager', 'employee', 'rh', 'admin']}>
          <Layout><Notifications /></Layout>
        </PrivateRoute>
      } />

      {/* API Whitelist — admin only */}
      <Route path="/whitelist" element={
        <PrivateRoute allowedRoles={['admin']}>
          <Layout><ApiWhitelist /></Layout>
        </PrivateRoute>
      } />

      {/* Audit Logs — admin only */}
      <Route path="/logs" element={
        <PrivateRoute allowedRoles={['admin']}>
          <Layout><AuditLogs /></Layout>
        </PrivateRoute>
      } />

      {/* Root redirect */}
      <Route path="/" element={<Navigate to={isAuthenticated ? getHomePage(user) : '/login'} />} />

      {/* Catch all */}
      <Route path="*" element={<Navigate to={isAuthenticated ? getHomePage(user) : '/login'} />} />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;