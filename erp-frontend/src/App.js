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

const PrivateRoute = ({ children }) => {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? children : <Navigate to="/login" />;
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
      <Route
        path="/login"
        element={
          isAuthenticated
            ? user?.must_change_password
              ? <Navigate to="/change-password" />
              : <Navigate to="/dashboard" />
            : <Login />
        }
      />
      <Route path="/change-password" element={<ChangePassword />} />
      <Route path="/dashboard"      element={<PrivateRoute><Layout><Dashboard /></Layout></PrivateRoute>} />
      <Route path="/projects"       element={<PrivateRoute><Layout><Projects /></Layout></PrivateRoute>} />
      <Route path="/employees"      element={<PrivateRoute><Layout><Employees /></Layout></PrivateRoute>} />
      <Route path="/kpis"           element={<PrivateRoute><Layout><KPIs /></Layout></PrivateRoute>} />
      <Route path="/leave-requests" element={<PrivateRoute><Layout><LeaveRequests /></Layout></PrivateRoute>} />
      <Route path="/clients"        element={<PrivateRoute><Layout><Clients /></Layout></PrivateRoute>} />
      <Route path="/tasks"          element={<PrivateRoute><Layout><Tasks /></Layout></PrivateRoute>} />
      <Route path="/reports"        element={<PrivateRoute><Layout><Reports /></Layout></PrivateRoute>} />
      <Route path="/notifications"  element={<PrivateRoute><Layout><Notifications /></Layout></PrivateRoute>} />
      <Route path="/issues"         element={<PrivateRoute><Layout><Issues /></Layout></PrivateRoute>} />
      <Route path="/"               element={<Navigate to="/dashboard" />} />
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