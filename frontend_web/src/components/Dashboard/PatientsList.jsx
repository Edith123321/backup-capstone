// frontend_web/src/components/Dashboard/PatientsList.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../context/AuthContext';
import { databaseApi } from '../../services/api';
import { useNavigate } from 'react-router-dom';
import './PatientList.css';

const PatientsList = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);
  const [isMobile, setIsMobile] = useState(false);
  const [stats, setStats] = useState({
    total: 0,
    male: 0,
    female: 0,
    children: 0
  });

  // Check if mobile view
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
      // Adjust items per page for mobile
      if (window.innerWidth < 768) {
        setItemsPerPage(5);
      } else {
        setItemsPerPage(10);
      }
    };
    
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  useEffect(() => {
    if (user?.id) {
      fetchPatients();
    }
  }, [user]);

  const fetchPatients = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await databaseApi.getPatients(user.id);
      
      if (response.success) {
        const patientData = response.patients || [];
        setPatients(patientData);
        
        const statsData = {
          total: patientData.length,
          male: patientData.filter(p => p.gender?.toLowerCase() === 'male').length,
          female: patientData.filter(p => p.gender?.toLowerCase() === 'female').length,
          children: patientData.filter(p => (p.age || 0) < 18).length
        };
        setStats(statsData);
      } else {
        setError(response.error || 'Failed to load patients');
      }
    } catch (error) {
      console.error('Error fetching patients:', error);
      setError(error.message || 'Failed to connect to server');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (event) => {
    setSearchTerm(event.target.value);
    setCurrentPage(1);
  };

  // Navigate to patient profile
  const handleViewPatient = (patientId) => {
    navigate(`/patient/${patientId}`);
  };

  // Handle mobile card click
  const handlePatientCardClick = (patientId) => {
    handleViewPatient(patientId);
  };

  const handleNewPatient = () => {
    navigate('/encounter/new');
  };

  const getAgeGroup = (age) => {
    if (!age) return 'Unknown';
    if (age < 2) return 'Infant';
    if (age < 12) return 'Child';
    if (age < 18) return 'Adolescent';
    if (age < 60) return 'Adult';
    return 'Elderly';
  };

  const getRHDStatusDisplay = (status) => {
    const statusMap = {
      'confirmed': { label: 'Confirmed RHD', color: '#dc2626', bg: '#fee2e2' },
      'suspected': { label: 'Suspected RHD', color: '#f59e0b', bg: '#fed7aa' },
      'none': { label: 'No RHD', color: '#22c55e', bg: '#dcfce7' },
      'unknown': { label: 'Unknown', color: '#94a3b8', bg: '#f1f5f9' }
    };
    return statusMap[status] || statusMap.unknown;
  };

  // Filter patients
  const filteredPatients = patients.filter(patient => {
    const searchLower = searchTerm.toLowerCase();
    return (
      patient.name?.toLowerCase().includes(searchLower) ||
      patient.contact?.includes(searchTerm) ||
      patient.address?.toLowerCase().includes(searchLower) ||
      patient.id?.toLowerCase().includes(searchLower)
    );
  });

  // Pagination
  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentPatients = filteredPatients.slice(indexOfFirstItem, indexOfLastItem);
  const totalPages = Math.ceil(filteredPatients.length / itemsPerPage);

  const paginate = (pageNumber) => setCurrentPage(pageNumber);

  if (loading) {
    return (
      <div className="patients-loading">
        <div className="loading-spinner"></div>
        <p>Loading patients...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="patients-error">
        <div className="error-content">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#dc2626" strokeWidth="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <h3>Error Loading Patients</h3>
          <p>{error}</p>
          <button className="btn-retry" onClick={fetchPatients}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M23 4v6h-6"/>
              <path d="M1 20v-6h6"/>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10"/>
              <path d="M20.49 15a9 9 0 0 1-14.85 3.36L1 14"/>
            </svg>
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="patients-container">
      <div className="patients-header">
        <div>
          <h1 className="patients-title">Patients</h1>
          <p className="patients-subtitle">Manage and view all patient records</p>
        </div>
        <button className="btn-primary" onClick={handleNewPatient}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          New Patient
        </button>
      </div>

      {/* Stats Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon stat-icon-total">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
            </svg>
          </div>
          <div className="stat-info">
            <span className="stat-number">{stats.total}</span>
            <span className="stat-label">Total Patients</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon stat-icon-male">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="4"/>
              <line x1="12" y1="5" x2="12" y2="2"/>
              <line x1="12" y1="22" x2="12" y2="19"/>
              <line x1="5" y1="12" x2="2" y2="12"/>
              <line x1="22" y1="12" x2="19" y2="12"/>
            </svg>
          </div>
          <div className="stat-info">
            <span className="stat-number">{stats.male}</span>
            <span className="stat-label">Male</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon stat-icon-female">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="4"/>
              <path d="M12 16v6"/>
              <path d="M9 19h6"/>
            </svg>
          </div>
          <div className="stat-info">
            <span className="stat-number">{stats.female}</span>
            <span className="stat-label">Female</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon stat-icon-children">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5"/>
              <path d="M2 12l10 5 10-5"/>
            </svg>
          </div>
          <div className="stat-info">
            <span className="stat-number">{stats.children}</span>
            <span className="stat-label">Children (Under 18)</span>
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="table-toolbar">
        <div className="search-wrapper">
          <svg className="search-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input
            type="text"
            className="search-input"
            placeholder={isMobile ? "Search patients..." : "Search patients by name, contact, or address..."}
            value={searchTerm}
            onChange={handleSearch}
          />
        </div>
        <span className="patient-count">{filteredPatients.length} patients found</span>
      </div>

      {/* Mobile View - Cards */}
      {isMobile ? (
        <div className="patients-mobile-grid">
          {currentPatients.length === 0 ? (
            <div className="empty-state-mobile">
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="1.5">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                <circle cx="9" cy="7" r="4"/>
                <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
              </svg>
              <p>{searchTerm ? 'No patients match your search' : 'No patients found'}</p>
              {!searchTerm && (
                <button className="btn-primary" onClick={handleNewPatient}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="12" y1="5" x2="12" y2="19"/>
                    <line x1="5" y1="12" x2="19" y2="12"/>
                  </svg>
                  Add Your First Patient
                </button>
              )}
            </div>
          ) : (
            currentPatients.map((patient) => {
              const rhdStatus = getRHDStatusDisplay(patient.rhd_status);
              return (
                <div 
                  key={patient.id} 
                  className="patient-card-mobile"
                  onClick={() => handlePatientCardClick(patient.id)}
                >
                  <div className="patient-card-header">
                    <div className="patient-avatar">
                      {patient.name?.charAt(0) || 'P'}
                    </div>
                    <div className="patient-card-name">
                      <h3>{patient.name || 'Unnamed Patient'}</h3>
                      <span className="patient-id">ID: {patient.id}</span>
                    </div>
                    <span 
                      className="rhd-status-badge"
                      style={{ 
                        backgroundColor: rhdStatus.bg,
                        color: rhdStatus.color 
                      }}
                    >
                      {rhdStatus.label}
                    </span>
                  </div>
                  
                  <div className="patient-card-details">
                    <div className="detail-item">
                      <span className="detail-label">Age</span>
                      <span className="detail-value">{patient.age || '—'} years</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Gender</span>
                      <span className={`gender-badge gender-${patient.gender?.toLowerCase() || 'unknown'}`}>
                        {patient.gender || 'Unknown'}
                      </span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Contact</span>
                      <span className="detail-value">{patient.contact || '—'}</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Address</span>
                      <span className="detail-value address-truncate">{patient.address || '—'}</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Age Group</span>
                      <span className="age-group-badge">{getAgeGroup(patient.age)}</span>
                    </div>
                  </div>
                  
                  <div className="patient-card-actions">
                    <button 
                      className="btn-view-mobile"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleViewPatient(patient.id);
                      }}
                    >
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                        <circle cx="12" cy="12" r="3"/>
                      </svg>
                      View Profile
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      ) : (
        /* Desktop View - Table */
        <div className="table-container">
          <table className="patients-table">
            <thead>
              <tr>
                <th>Patient</th>
                <th>Age</th>
                <th>Gender</th>
                <th>Contact</th>
                <th>Address</th>
                <th className="text-center">Actions</th>
              </tr>
            </thead>
            <tbody>
              {currentPatients.length === 0 ? (
                <tr>
                  <td colSpan="6" className="empty-state">
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="1.5">
                      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                      <circle cx="9" cy="7" r="4"/>
                      <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                      <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                    </svg>
                    <p>{searchTerm ? 'No patients match your search' : 'No patients found'}</p>
                    {!searchTerm && (
                      <button className="btn-primary" onClick={handleNewPatient}>
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <line x1="12" y1="5" x2="12" y2="19"/>
                          <line x1="5" y1="12" x2="19" y2="12"/>
                        </svg>
                        Add Your First Patient
                      </button>
                    )}
                  </td>
                </tr>
              ) : (
                currentPatients.map((patient) => {
                  const rhdStatus = getRHDStatusDisplay(patient.rhd_status);
                  return (
                    <tr key={patient.id}>
                      <td>
                        <div className="patient-name">
                          <div className="patient-avatar">
                            {patient.name?.charAt(0) || 'P'}
                          </div>
                          <div>
                            <span>{patient.name || 'Unnamed Patient'}</span>
                            {patient.rhd_status && (
                              <span 
                                className="rhd-status-dot"
                                style={{ 
                                  backgroundColor: rhdStatus.color,
                                  display: 'inline-block',
                                  width: '8px',
                                  height: '8px',
                                  borderRadius: '50%',
                                  marginLeft: '8px'
                                }}
                              />
                            )}
                          </div>
                        </div>
                      </td>
                      <td>
                        <span className="age-badge">{patient.age || '—'}</span>
                        {patient.age && (
                          <span className="age-group-badge">{getAgeGroup(patient.age)}</span>
                        )}
                      </td>
                      <td>
                        <span className={`gender-badge gender-${patient.gender?.toLowerCase() || 'unknown'}`}>
                          {patient.gender || 'Unknown'}
                        </span>
                      </td>
                      <td>{patient.contact || '—'}</td>
                      <td className="address-cell">{patient.address || '—'}</td>
                      <td className="text-center">
                        <button
                          className="btn-view"
                          onClick={() => handleViewPatient(patient.id)}
                          title="View Patient"
                        >
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                            <circle cx="12" cy="12" r="3"/>
                          </svg>
                          View
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {filteredPatients.length > 0 && (
        <div className="pagination">
          <div className="pagination-info">
            Showing {indexOfFirstItem + 1} to {Math.min(indexOfLastItem, filteredPatients.length)} of {filteredPatients.length} patients
          </div>
          <div className="pagination-controls">
            <button
              className="pagination-btn"
              onClick={() => paginate(currentPage - 1)}
              disabled={currentPage === 1}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="15 18 9 12 15 6"/>
              </svg>
            </button>
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
              let pageNum;
              if (totalPages <= 5) {
                pageNum = i + 1;
              } else if (currentPage <= 3) {
                pageNum = i + 1;
              } else if (currentPage >= totalPages - 2) {
                pageNum = totalPages - 4 + i;
              } else {
                pageNum = currentPage - 2 + i;
              }
              return (
                <button
                  key={pageNum}
                  className={`pagination-btn ${currentPage === pageNum ? 'active' : ''}`}
                  onClick={() => paginate(pageNum)}
                >
                  {pageNum}
                </button>
              );
            })}
            <button
              className="pagination-btn"
              onClick={() => paginate(currentPage + 1)}
              disabled={currentPage === totalPages}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="9 18 15 12 9 6"/>
              </svg>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default PatientsList;