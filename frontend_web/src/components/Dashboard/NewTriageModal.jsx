// frontend_web/src/components/Dashboard/NewTriageModal.jsx
import React, { useState } from 'react';
import { databaseApi } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import './DashboardLayout.css';

const NewTriageModal = ({ isOpen, onClose, onTriageCreated, patients, preSelectedPatient }) => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    patient_id: preSelectedPatient?.id || '',
    age: preSelectedPatient?.age || '',
    gender: preSelectedPatient?.gender || '',
    weight: '',
    temperature: '',
    blood_pressure_systolic: '',
    blood_pressure_diastolic: '',
    heart_rate: '',
    symptoms: '',
    notes: ''
  });

  // Update form when preSelectedPatient changes
  React.useEffect(() => {
    if (preSelectedPatient) {
      setFormData(prev => ({
        ...prev,
        patient_id: preSelectedPatient.id,
        age: preSelectedPatient.age || '',
        gender: preSelectedPatient.gender || ''
      }));
    }
  }, [preSelectedPatient]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await databaseApi.createTriage({
        ...formData,
        doctor_id: user.id
      });

      if (response.success) {
        onTriageCreated();
        onClose();
        setFormData({
          patient_id: preSelectedPatient?.id || '',
          age: preSelectedPatient?.age || '',
          gender: preSelectedPatient?.gender || '',
          weight: '',
          temperature: '',
          blood_pressure_systolic: '',
          blood_pressure_diastolic: '',
          heart_rate: '',
          symptoms: '',
          notes: ''
        });
      } else {
        setError(response.error || 'Failed to create triage record');
      }
    } catch (err) {
      setError('An error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>New Triage</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        {error && (
          <div className="modal-error">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="form-group">
              <label>Patient</label>
              <select
                name="patient_id"
                value={formData.patient_id}
                onChange={handleChange}
                required
                disabled={!!preSelectedPatient}
              >
                <option value="">Select a patient</option>
                {patients.map(patient => (
                  <option key={patient.id} value={patient.id}>
                    {patient.name} (ID: {patient.id})
                  </option>
                ))}
              </select>
              {preSelectedPatient && (
                <div className="form-hint">
                  Patient: {preSelectedPatient.name} (ID: {preSelectedPatient.id})
                </div>
              )}
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Age</label>
                <input
                  type="number"
                  name="age"
                  value={formData.age}
                  onChange={handleChange}
                  required
                  disabled={!!preSelectedPatient}
                  placeholder="Enter age"
                />
              </div>
              <div className="form-group">
                <label>Gender</label>
                <select
                  name="gender"
                  value={formData.gender}
                  onChange={handleChange}
                  required
                  disabled={!!preSelectedPatient}
                >
                  <option value="">Select</option>
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                  <option value="Other">Other</option>
                </select>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Weight (kg)</label>
                <input
                  type="number"
                  name="weight"
                  value={formData.weight}
                  onChange={handleChange}
                  step="0.1"
                  placeholder="Enter weight"
                />
              </div>
              <div className="form-group">
                <label>Temperature (°C)</label>
                <input
                  type="number"
                  name="temperature"
                  value={formData.temperature}
                  onChange={handleChange}
                  step="0.1"
                  placeholder="Enter temperature"
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Blood Pressure (Systolic)</label>
                <input
                  type="number"
                  name="blood_pressure_systolic"
                  value={formData.blood_pressure_systolic}
                  onChange={handleChange}
                  placeholder="e.g., 120"
                />
              </div>
              <div className="form-group">
                <label>Blood Pressure (Diastolic)</label>
                <input
                  type="number"
                  name="blood_pressure_diastolic"
                  value={formData.blood_pressure_diastolic}
                  onChange={handleChange}
                  placeholder="e.g., 80"
                />
              </div>
            </div>

            <div className="form-group">
              <label>Heart Rate (bpm)</label>
              <input
                type="number"
                name="heart_rate"
                value={formData.heart_rate}
                onChange={handleChange}
                placeholder="Enter heart rate"
              />
            </div>

            <div className="form-group">
              <label>Symptoms</label>
              <textarea
                name="symptoms"
                value={formData.symptoms}
                onChange={handleChange}
                rows="2"
                placeholder="Describe any symptoms..."
              />
            </div>

            <div className="form-group">
              <label>Notes</label>
              <textarea
                name="notes"
                value={formData.notes}
                onChange={handleChange}
                rows="2"
                placeholder="Additional notes..."
              />
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Creating...' : 'Create Triage'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default NewTriageModal;