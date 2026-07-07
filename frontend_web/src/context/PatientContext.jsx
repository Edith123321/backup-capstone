import React, { createContext, useContext, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

const PatientContext = createContext();

export const PatientProvider = ({ children }) => {
  const [selectedPatient, setSelectedPatient] = useState(null);
  const navigate = useNavigate();

  const handlePatientSelect = useCallback((patient) => {
    setSelectedPatient(patient);
    navigate(`/patient/${patient.id}`);
  }, [navigate]);

  return (
    <PatientContext.Provider value={{ selectedPatient, setSelectedPatient, handlePatientSelect }}>
      {children}
    </PatientContext.Provider>
  );
};

export const usePatient = () => useContext(PatientContext);