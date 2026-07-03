// frontend_web/src/components/Patient/PatientHistory.jsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './Patient.css';

const PatientHistory = () => {
  const navigate = useNavigate();
  const [filter, setFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

  // Mock history data - replace with API call
  const historyData = [
    { id: 1, name: 'Sarah Kamau', age: 12, result: 'RHD', date: '2026-06-25', confidence: 97.2, doctor: 'Dr. Smith' },
    { id: 2, name: 'John Otieno', age: 8, result: 'Normal', date: '2026-06-25', confidence: 98.8, doctor: 'Dr. Jones' },
    { id: 3, name: 'Mary Wanjiku', age: 14, result: 'Normal', date: '2026-06-24', confidence: 99.1, doctor: 'Dr. Smith' },
    { id: 4, name: 'Peter Mwangi', age: 10, result: 'RHD', date: '2026-06-24', confidence: 95.8, doctor: 'Dr. Williams' },
    { id: 5, name: 'Grace Akinyi', age: 9, result: 'Normal', date: '2026-06-23', confidence: 97.5, doctor: 'Dr. Jones' },
    { id: 6, name: 'James Odhiambo', age: 11, result: 'RHD', date: '2026-06-23', confidence: 96.3, doctor: 'Dr. Smith' },
    { id: 7, name: 'Alice Muthoni', age: 13, result: 'Normal', date: '2026-06-22', confidence: 98.2, doctor: 'Dr. Williams' },
    { id: 8, name: 'David Ochieng', age: 7, result: 'Normal', date: '2026-06-22', confidence: 99.4, doctor: 'Dr. Jones' }
  ];

  const filteredData = historyData.filter(item => {
    if (filter !== 'all' && item.result !== filter) return false;
    if (searchTerm && !item.name.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="patient-history-container">
      <div className="history-header">
        <h1>📜 Patient History</h1>
        <p>Complete record of all heart sound screenings</p>
      </div>

      <div className="history-controls">
        <div className="search-section">
          <input
            type="text"
            placeholder="Search patients..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>
        <div className="filter-section">
          <button 
            className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
          >
            All
          </button>
          <button 
            className={`filter-btn ${filter === 'Normal' ? 'active' : ''}`}
            onClick={() => setFilter('Normal')}
          >
            Normal
          </button>
          <button 
            className={`filter-btn ${filter === 'RHD' ? 'active' : ''}`}
            onClick={() => setFilter('RHD')}
          >
            RHD
          </button>
        </div>
      </div>

      <div className="history-table-container">
        <table className="history-table">
          <thead>
            <tr>
              <th>Patient</th>
              <th>Age</th>
              <th>Result</th>
              <th>Date</th>
              <th>Confidence</th>
              <th>Doctor</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredData.map((item) => (
              <tr key={item.id}>
                <td className="patient-name-cell">
                  <span className="patient-avatar-small">
                    {item.name.charAt(0)}
                  </span>
                  {item.name}
                </td>
                <td>{item.age}</td>
                <td>
                  <span className={`badge ${item.result === 'RHD' ? 'rhd' : 'normal'}`}>
                    {item.result}
                  </span>
                </td>
                <td>{item.date}</td>
                <td>{item.confidence}%</td>
                <td>{item.doctor}</td>
                <td>
                  <button 
                    className="view-btn"
                    onClick={() => navigate(`/patient/${item.id}`)}
                  >
                    View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="history-stats">
        <div className="stat-item">
          <span className="stat-label">Total Screenings</span>
          <span className="stat-value">{historyData.length}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Normal</span>
          <span className="stat-value normal">
            {historyData.filter(h => h.result === 'Normal').length}
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">RHD</span>
          <span className="stat-value rhd">
            {historyData.filter(h => h.result === 'RHD').length}
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Avg Confidence</span>
          <span className="stat-value">
            {(historyData.reduce((sum, h) => sum + h.confidence, 0) / historyData.length).toFixed(1)}%
          </span>
        </div>
      </div>
    </div>
  );
};

export default PatientHistory;