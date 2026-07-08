// frontend_web/src/components/Dashboard/DoctorDashboard.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation, useParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { databaseApi, patientService } from '../../services/api';
import './DashboardLayout.css';

// Components
import Sidebar from './Sidebar';
import StatsCards from './StatsCards';
import PatientsList from './PatientsList';
import TriageSection from './TriageSection';
import NewTriageModal from './NewTriageModal';
import UploadHeartSound from './UploadHeartSound';
import IoTDevices from './IoTDevices';
import RecordingsView from './RecordingsView';
import PatientProfile from './PatientProfile';
import NewEncounter from './NewEncounter';
import PatientHistory from '../Patient/PatientHistory';
import OfflineBanner from '../Common/OfflineBanner';
import { warmUpBackend } from '../../services/resilientFetch';

const DoctorDashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const params = useParams();
  
  // State
  const [patients, setPatients] = useState([]);
  const [triageRecords, setTriageRecords] = useState([]);
  const [recordings, setRecordings] = useState([]);
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNewTriage, setShowNewTriage] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [selectedPatient, setSelectedPatient] = useState(null);
  
  // Stats state
  const [stats, setStats] = useState({
    totalPatients: 0,
    todayScreenings: 0,
    totalRecordings: 0,
    flagged: 0
  });

  // Determine active section from current route
  const getActiveSection = () => {
    const path = location.pathname;
    
    if (path === '/dashboard') return 'dashboard';
    if (path === '/patients') return 'patients';
    if (path === '/recordings') return 'recordings';
    if (path === '/devices') return 'devices';
    if (path === '/encounter/new') return 'new-encounter';
    if (path === '/history') return 'history';
    if (path.startsWith('/patient/')) return 'patient';
    
    return 'dashboard';
  };

  const activeSection = getActiveSection();

  // Wake the (possibly spun-down) backend as soon as the dashboard loads, so
  // it's warm by the time the nurse submits an encounter/recording.
  useEffect(() => {
    warmUpBackend();
  }, []);

  // Fetch patient details when on patient page
  useEffect(() => {
    if (activeSection === 'patient' && params.id && patients.length > 0) {
      const patient = patients.find(p => p.id === parseInt(params.id) || p.id === params.id);
      if (patient) {
        setSelectedPatient(patient);
      }
    }
  }, [activeSection, params.id, patients]);

  // Fetch all dashboard data
  const fetchDashboardData = useCallback(async () => {
    if (!user?.id) return;
    
    try {
      setLoading(true);
      
      // Fetch patients
      const patientsData = await patientService.getPatients(user.id);
      const patientsList = patientsData || [];
      setPatients(patientsList);
      
      // Fetch triage records
      const triageResponse = await databaseApi.getTriageByDoctor(user.id);
      const triageData = triageResponse?.triage || [];
      setTriageRecords(triageData);
      
      // Fetch recordings
      const recordingsData = [];
      for (const patient of patientsList) {
        const response = await databaseApi.getRecordings(patient.id);
        if (response.success && response.recordings) {
          recordingsData.push(...response.recordings);
        }
      }
      setRecordings(recordingsData);
      
      // Fetch devices
      const devicesResponse = await databaseApi.getDevices(user.id);
      const devicesData = devicesResponse?.devices || [];
      setDevices(devicesData);
      
      // Update stats
      const today = new Date().toDateString();
      const todayScreenings = triageData.filter(t => 
        t.created_at && new Date(t.created_at).toDateString() === today
      ).length;
      
      setStats({
        totalPatients: patientsList.length,
        todayScreenings: todayScreenings,
        totalRecordings: recordingsData.length,
        flagged: triageData.filter(t => 
          t.triage_color === 'Red' || t.triage_color === 'Orange'
        ).length
      });
      
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  }, [user?.id]);

  // Initial data fetch
  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData, refreshTrigger]);

  // Handlers
  const handleRefresh = useCallback(() => {
    setRefreshTrigger(prev => prev + 1);
  }, []);

  const handleSectionChange = useCallback((section) => {
    // Navigate to the corresponding route
    const routes = {
      dashboard: '/dashboard',
      patients: '/patients',
      recordings: '/recordings',
      devices: '/devices',
      'new-encounter': '/encounter/new',
      history: '/history'
    };
    
    if (routes[section]) {
      navigate(routes[section]);
    }
  }, [navigate]);

  const handlePatientSelect = useCallback((patient) => {
    setSelectedPatient(patient);
    navigate(`/patient/${patient.id}`);
  }, [navigate]);

  const handleTriageCreated = useCallback(() => {
    handleRefresh();
  }, [handleRefresh]);

  const handleUploadComplete = useCallback(() => {
    handleRefresh();
  }, [handleRefresh]);

  // Render content based on active section
  const renderContent = () => {
    switch (activeSection) {
      case 'new-encounter':
        return (
          <NewEncounter onComplete={() => {
            handleRefresh();
            navigate('/patients');
          }} />
        );

      case 'patient':
        return (
          <div className="section-content">
            <button className="back-btn" onClick={() => navigate('/patients')}>
              ← Back to Patients
            </button>
            <PatientProfile 
              patient={selectedPatient} 
              triageRecords={triageRecords.filter(t => t.patient_id === selectedPatient?.id)}
              recordings={recordings.filter(r => r.patient_id === selectedPatient?.id)}
              onBack={() => navigate('/patients')}
              onNewTriage={() => {
                setShowNewTriage(true);
              }}
              onNewRecording={() => {
                setShowUpload(true);
              }}
            />
          </div>
        );

      case 'patients':
        return (
          <div className="section-content">
            <div className="section-header">
              <h1>Patients</h1>
              <button className="btn-primary" onClick={() => navigate('/encounter/new')}>
                <span className="btn-icon">+</span>
                Add Patient
              </button>
            </div>
            <PatientsList 
              patients={patients} 
              onPatientSelect={handlePatientSelect}
              showActions={true}
            />
          </div>
        );

      case 'recordings':
        return (
          <div className="section-content">
            <div className="section-header">
              <h1>Heart Sound Recordings</h1>
              <button className="btn-upload" onClick={() => setShowUpload(true)}>
                <span className="btn-icon">↑</span>
                Upload New
              </button>
            </div>
            <RecordingsView 
              recordings={recordings}
              patients={patients}
              onRefresh={handleRefresh}
            />
          </div>
        );

      case 'devices':
        return (
          <div className="section-content">
            <div className="section-header">
              <h1>IoT Devices</h1>
            </div>
            <IoTDevices devices={devices} onRefresh={handleRefresh} />
          </div>
        );

      case 'history':
        return (
          <div className="section-content">
            <div className="section-header">
              <h1>Patient History</h1>
            </div>
            <PatientHistory />
          </div>
        );

      case 'dashboard':
      default:
        return (
          <>
            {/* Header */}
            <div className="dashboard-header">
              <div className="welcome-section">
                <h1>Welcome back, Dr. {user?.name?.split(' ')[0] || 'Doctor'}</h1>
                <p>Here's what's happening with your patients today</p>
              </div>
              <div className="dashboard-actions">
                <button className="btn-primary" onClick={() => setShowNewTriage(true)}>
                  <span className="btn-icon">+</span>
                  New Triage
                </button>
                <button className="btn-upload" onClick={() => setShowUpload(true)}>
                  <span className="btn-icon">↑</span>
                  Upload Sound
                </button>
              </div>
            </div>

            {/* Stats */}
            <StatsCards stats={stats} />

            {/* Main Grid */}
            <div className="dashboard-grid">
              <div className="grid-left">
                <PatientsList patients={patients} onPatientSelect={handlePatientSelect} />
                <TriageSection 
                  triageRecords={triageRecords} 
                  onRefresh={handleRefresh}
                  onPatientSelect={handlePatientSelect}
                />
              </div>
            </div>
          </>
        );
    }
  };

  // Loading state
  if (loading && activeSection === 'dashboard') {
    return (
      <div className="loading-container">
        <div className="loading-spinner" />
        <p>Loading dashboard...</p>
      </div>
    );
  }

  return (
    <div className="dashboard-layout-wrapper">
      <Sidebar 
        activeSection={activeSection} 
        onSectionChange={handleSectionChange}
        user={user}
      />
      
      {/* Main Content Area */}
      <div className="dashboard-content">
        {/* Scenario 4 — offline / pending-sync status banner */}
        <OfflineBanner />
        <div className="dashboard-container">
          {renderContent()}
        </div>
      </div>

      {/* Modals - Pass preSelectedPatient */}
      <NewTriageModal
        isOpen={showNewTriage}
        onClose={() => setShowNewTriage(false)}
        onTriageCreated={handleTriageCreated}
        patients={patients}
        preSelectedPatient={selectedPatient}
      />

      <UploadHeartSound
        isOpen={showUpload}
        onClose={() => setShowUpload(false)}
        onUploadComplete={handleUploadComplete}
        patients={patients}
        preSelectedPatient={selectedPatient}
      />
    </div>
  );
};

export default DoctorDashboard;