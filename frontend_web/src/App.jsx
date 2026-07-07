// frontend_web/src/App.jsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import './App.css';

// Components - Auth
import Login from './components/Auth/Login';
import AuthCallback from './components/Auth/AuthCallback';

// Components - Common
import LoadingSpinner from './components/Common/LoadingSpinner';

// Components - Dashboard
import DoctorDashboard from './components/Dashboard/DoctorDashboard';
import NewEncounter from './components/Dashboard/NewEncounter';
import PatientProfile from './components/Dashboard/PatientProfile';
import PatientsList from './components/Dashboard/PatientsList';
import IoTDevices from './components/Dashboard/IoTDevices';
import RecordingsView from './components/Dashboard/RecordingsView';

// Components - Landing
import LandingPage from './components/Landing/LandingPage';

// Components - Patient
import PatientDetails from './components/Patient/PatientDetails';
import PatientHistory from './components/Patient/PatientHistory';

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return <LoadingSpinner message="Loading your dashboard..." />;
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }
  
  return children;
};

function AppContent() {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<Login />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      
      {/* Protected Routes - All dashboard routes use DoctorDashboard */}
      <Route path="/dashboard" element={
        <ProtectedRoute>
          <DoctorDashboard />
        </ProtectedRoute>
      } />
      
      <Route path="/patients" element={
        <ProtectedRoute>
          <DoctorDashboard />
        </ProtectedRoute>
      } />
      
      <Route path="/recordings" element={
        <ProtectedRoute>
          <DoctorDashboard />
        </ProtectedRoute>
      } />
      
      <Route path="/devices" element={
        <ProtectedRoute>
          <DoctorDashboard />
        </ProtectedRoute>
      } />
      
      <Route path="/encounter/new" element={
        <ProtectedRoute>
          <DoctorDashboard />
        </ProtectedRoute>
      } />
      
      <Route path="/patient/:id" element={
        <ProtectedRoute>
          <Pa />
        </ProtectedRoute>
      } />
      
      <Route path="/history" element={
        <ProtectedRoute>
          <DoctorDashboard />
        </ProtectedRoute>
      } />
      
      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </Router>
  );
}

export default App;