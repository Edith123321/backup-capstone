# backend/services/database.py
import os
import json
from datetime import datetime
import sqlite3
from typing import Dict, List, Optional
import uuid

class DoctorDatabase:
    """Database service for storing doctor information and predictions"""
    
    def __init__(self, db_path='doctors.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Doctors table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS doctors (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                picture TEXT,
                specialty TEXT,
                hospital TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        # Patients table with RHD status
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                id TEXT PRIMARY KEY,
                doctor_id TEXT NOT NULL,
                name TEXT NOT NULL,
                age INTEGER,
                gender TEXT,
                date_of_birth TEXT,
                contact TEXT,
                address TEXT,
                emergency_contact TEXT,
                medical_history TEXT,
                rhd_status TEXT DEFAULT 'unknown',
                rhd_diagnosis_date TEXT,
                rhd_treatment TEXT,
                rhd_notes TEXT,
                last_rhd_assessment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doctor_id) REFERENCES doctors (id)
            )
        ''')
        
        # Triage records table (Jones Triage System)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS triage_records (
                id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                doctor_id TEXT NOT NULL,
                triage_level TEXT NOT NULL,
                triage_color TEXT NOT NULL,
                triage_score INTEGER,
                respiratory_rate REAL,
                heart_rate REAL,
                oxygen_saturation REAL,
                temperature REAL,
                blood_pressure_systolic INTEGER,
                blood_pressure_diastolic INTEGER,
                consciousness_level TEXT,
                pain_score INTEGER,
                chief_complaint TEXT,
                symptoms TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients (id),
                FOREIGN KEY (doctor_id) REFERENCES doctors (id)
            )
        ''')
        
        # Heart sound recordings table (for IoT stethoscope)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS heart_sound_recordings (
                id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                doctor_id TEXT NOT NULL,
                recording_data TEXT,
                file_path TEXT,
                file_name TEXT,
                file_url TEXT,
                duration REAL,
                frequency_range TEXT,
                quality_score REAL,
                prediction TEXT,
                confidence REAL,
                probabilities TEXT,
                rhd_risk_score REAL,
                rhd_recommendation TEXT,
                recording_date TIMESTAMP,
                notes TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                analyzed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients (id),
                FOREIGN KEY (doctor_id) REFERENCES doctors (id)
            )
        ''')
        
        # IoT Devices table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS iot_devices (
                id TEXT PRIMARY KEY,
                doctor_id TEXT NOT NULL,
                device_name TEXT NOT NULL,
                device_type TEXT,
                ip_address TEXT,
                mac_address TEXT,
                status TEXT DEFAULT 'offline',
                last_connected TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doctor_id) REFERENCES doctors (id)
            )
        ''')
        
        # Follow-up reminders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS follow_up_reminders (
                id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                recommended_days INTEGER,
                reason TEXT,
                completed BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients (id)
            )
        ''')
        
        # Add missing columns if they don't exist
        try:
            cursor.execute("ALTER TABLE patients ADD COLUMN rhd_status TEXT DEFAULT 'unknown'")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE patients ADD COLUMN rhd_diagnosis_date TEXT")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE patients ADD COLUMN rhd_treatment TEXT")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE patients ADD COLUMN rhd_notes TEXT")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE patients ADD COLUMN last_rhd_assessment TEXT")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE heart_sound_recordings ADD COLUMN file_name TEXT")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE heart_sound_recordings ADD COLUMN file_url TEXT")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE heart_sound_recordings ADD COLUMN notes TEXT")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE heart_sound_recordings ADD COLUMN recording_date TIMESTAMP")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE heart_sound_recordings ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE heart_sound_recordings ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE triage_records ADD COLUMN triage_score INTEGER")
        except sqlite3.OperationalError:
            pass
        
        conn.commit()
        conn.close()
    
    # ============ HELPER METHODS ============
    
    def _safe_int(self, value, default=0):
        """Safely convert value to int"""
        if value is None or value == '':
            return default
        try:
            return int(float(value)) if isinstance(value, (int, float, str)) else default
        except (ValueError, TypeError):
            return default
    
    def _safe_float(self, value, default=0.0):
        """Safely convert value to float"""
        if value is None or value == '':
            return default
        try:
            return float(value) if isinstance(value, (int, float, str)) else default
        except (ValueError, TypeError):
            return default
    
    def get_connection(self):
        """Get a database connection"""
        return sqlite3.connect(self.db_path)
    
    # ============ DOCTOR METHODS ============
    
    def save_doctor(self, user_data: Dict) -> bool:
        """Save or update doctor information"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO doctors (id, email, name, picture, last_login)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                user_data.get('id'),
                user_data.get('email'),
                user_data.get('name'),
                user_data.get('picture')
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving doctor: {e}")
            return False
    
    def get_doctor(self, doctor_id: str) -> Optional[Dict]:
        """Get doctor by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM doctors WHERE id = ?', (doctor_id,))
            row = cursor.fetchone()
            
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'email': row[1],
                    'name': row[2],
                    'picture': row[3],
                    'specialty': row[4],
                    'hospital': row[5],
                    'created_at': row[6],
                    'last_login': row[7]
                }
            return None
            
        except Exception as e:
            print(f"Error getting doctor: {e}")
            return None
    
    def update_doctor_profile(self, doctor_id: str, data: Dict) -> bool:
        """Update doctor profile"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE doctors 
                SET specialty = ?, hospital = ?, last_login = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (data.get('specialty'), data.get('hospital'), doctor_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating doctor: {e}")
            return False
    
    # ============ PATIENT METHODS WITH RHD ============
    
    def create_patient(self, doctor_id: str, data: Dict) -> Optional[str]:
        """Create a new patient for a doctor with RHD status"""
        try:
            patient_id = str(uuid.uuid4())[:8]
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get RHD status or default to 'unknown'
            rhd_status = data.get('rhd_status', 'unknown')
            if rhd_status not in ['none', 'suspected', 'confirmed', 'unknown']:
                rhd_status = 'unknown'
            
            cursor.execute('''
                INSERT INTO patients (
                    id, doctor_id, name, age, gender, date_of_birth,
                    contact, address, emergency_contact, medical_history,
                    rhd_status, rhd_diagnosis_date, rhd_treatment, rhd_notes, last_rhd_assessment
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                patient_id,
                doctor_id,
                data.get('name'),
                self._safe_int(data.get('age')),
                data.get('gender'),
                data.get('date_of_birth'),
                data.get('contact'),
                data.get('address'),
                data.get('emergency_contact'),
                data.get('medical_history'),
                rhd_status,
                data.get('rhd_diagnosis_date'),
                data.get('rhd_treatment'),
                data.get('rhd_notes'),
                datetime.now().isoformat() if rhd_status != 'unknown' else None
            ))
            
            conn.commit()
            conn.close()
            return patient_id
            
        except Exception as e:
            print(f"Error creating patient: {e}")
            return None
    
    def update_patient_rhd_status(self, patient_id: str, data: Dict) -> bool:
        """Update patient RHD status and related information"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            rhd_status = data.get('rhd_status', 'unknown')
            if rhd_status not in ['none', 'suspected', 'confirmed', 'unknown']:
                rhd_status = 'unknown'
            
            cursor.execute('''
                UPDATE patients 
                SET rhd_status = ?,
                    rhd_diagnosis_date = ?,
                    rhd_treatment = ?,
                    rhd_notes = ?,
                    last_rhd_assessment = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                rhd_status,
                data.get('rhd_diagnosis_date'),
                data.get('rhd_treatment'),
                data.get('rhd_notes'),
                datetime.now().isoformat(),
                patient_id
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error updating patient RHD status: {e}")
            return False
    
    def get_patients_by_doctor(self, doctor_id: str) -> List[Dict]:
        """Get all patients for a doctor with RHD status"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM patients WHERE doctor_id = ? ORDER BY created_at DESC
            ''', (doctor_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            patients = []
            for row in rows:
                patients.append({
                    'id': row[0],
                    'doctor_id': row[1],
                    'name': row[2],
                    'age': row[3],
                    'gender': row[4],
                    'date_of_birth': row[5],
                    'contact': row[6],
                    'address': row[7],
                    'emergency_contact': row[8],
                    'medical_history': row[9],
                    'rhd_status': row[10] if len(row) > 10 else 'unknown',
                    'rhd_diagnosis_date': row[11] if len(row) > 11 else None,
                    'rhd_treatment': row[12] if len(row) > 12 else None,
                    'rhd_notes': row[13] if len(row) > 13 else None,
                    'last_rhd_assessment': row[14] if len(row) > 14 else None,
                    'created_at': row[15] if len(row) > 15 else None,
                    'updated_at': row[16] if len(row) > 16 else None
                })
            
            return patients
            
        except Exception as e:
            print(f"Error getting patients: {e}")
            return []
    
    def get_patient_by_id(self, patient_id: str) -> Optional[Dict]:
        """Get a specific patient by ID with RHD status"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM patients WHERE id = ?', (patient_id,))
            row = cursor.fetchone()
            
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'doctor_id': row[1],
                    'name': row[2],
                    'age': row[3],
                    'gender': row[4],
                    'date_of_birth': row[5],
                    'contact': row[6],
                    'address': row[7],
                    'emergency_contact': row[8],
                    'medical_history': row[9],
                    'rhd_status': row[10] if len(row) > 10 else 'unknown',
                    'rhd_diagnosis_date': row[11] if len(row) > 11 else None,
                    'rhd_treatment': row[12] if len(row) > 12 else None,
                    'rhd_notes': row[13] if len(row) > 13 else None,
                    'last_rhd_assessment': row[14] if len(row) > 14 else None,
                    'created_at': row[15] if len(row) > 15 else None,
                    'updated_at': row[16] if len(row) > 16 else None
                }
            return None
            
        except Exception as e:
            print(f"Error getting patient: {e}")
            return None
    
    def get_patients_by_rhd_status(self, doctor_id: str, rhd_status: str) -> List[Dict]:
        """Get patients filtered by RHD status"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM patients 
                WHERE doctor_id = ? AND rhd_status = ?
                ORDER BY created_at DESC
            ''', (doctor_id, rhd_status))
            
            rows = cursor.fetchall()
            conn.close()
            
            patients = []
            for row in rows:
                patients.append({
                    'id': row[0],
                    'doctor_id': row[1],
                    'name': row[2],
                    'age': row[3],
                    'gender': row[4],
                    'date_of_birth': row[5],
                    'contact': row[6],
                    'address': row[7],
                    'emergency_contact': row[8],
                    'medical_history': row[9],
                    'rhd_status': row[10] if len(row) > 10 else 'unknown',
                    'rhd_diagnosis_date': row[11] if len(row) > 11 else None,
                    'rhd_treatment': row[12] if len(row) > 12 else None,
                    'rhd_notes': row[13] if len(row) > 13 else None,
                    'last_rhd_assessment': row[14] if len(row) > 14 else None,
                    'created_at': row[15] if len(row) > 15 else None,
                    'updated_at': row[16] if len(row) > 16 else None
                })
            
            return patients
            
        except Exception as e:
            print(f"Error getting patients by RHD status: {e}")
            return []
    
    # ============ TRIAGE METHODS ============
    
    def create_triage(self, doctor_id: str, data: Dict) -> Optional[str]:
        """Create a new triage record using Jones Triage System"""
        try:
            triage_id = str(uuid.uuid4())[:8]
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Safely convert all numeric values
            respiratory_rate = self._safe_float(data.get('respiratory_rate'))
            heart_rate = self._safe_float(data.get('heart_rate'))
            oxygen_saturation = self._safe_float(data.get('oxygen_saturation'), 100)
            temperature = self._safe_float(data.get('temperature'), 37)
            blood_pressure_systolic = self._safe_int(data.get('blood_pressure_systolic'))
            blood_pressure_diastolic = self._safe_int(data.get('blood_pressure_diastolic'))
            pain_score = self._safe_int(data.get('pain_score'))
            
            # Prepare triage data with proper types
            triage_data = {
                'patient_id': data.get('patient_id'),
                'respiratory_rate': respiratory_rate,
                'heart_rate': heart_rate,
                'oxygen_saturation': oxygen_saturation,
                'temperature': temperature,
                'blood_pressure_systolic': blood_pressure_systolic,
                'blood_pressure_diastolic': blood_pressure_diastolic,
                'consciousness_level': data.get('consciousness_level', 'alert'),
                'pain_score': pain_score,
                'chief_complaint': data.get('chief_complaint', ''),
                'symptoms': data.get('symptoms', ''),
                'notes': data.get('notes', '')
            }
            
            # Calculate triage level based on Jones Triage System
            triage_level, triage_color, triage_score = self.calculate_jones_triage(triage_data)
            
            cursor.execute('''
                INSERT INTO triage_records (
                    id, patient_id, doctor_id, triage_level, triage_color, triage_score,
                    respiratory_rate, heart_rate, oxygen_saturation, temperature,
                    blood_pressure_systolic, blood_pressure_diastolic,
                    consciousness_level, pain_score, chief_complaint, symptoms, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                triage_id,
                triage_data['patient_id'],
                doctor_id,
                triage_level,
                triage_color,
                triage_score,
                triage_data['respiratory_rate'],
                triage_data['heart_rate'],
                triage_data['oxygen_saturation'],
                triage_data['temperature'],
                triage_data['blood_pressure_systolic'],
                triage_data['blood_pressure_diastolic'],
                triage_data['consciousness_level'],
                triage_data['pain_score'],
                triage_data['chief_complaint'],
                triage_data['symptoms'],
                triage_data['notes']
            ))
            
            conn.commit()
            conn.close()
            return triage_id
            
        except Exception as e:
            print(f"Error creating triage: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def calculate_jones_triage(self, data: Dict) -> tuple:
        """
        Jones Triage System - Color coded urgency levels
        Returns: (level, color, score)
        """
        score = 0
        
        # Respiratory Rate
        rr = data.get('respiratory_rate', 0)
        if isinstance(rr, str):
            rr = float(rr) if rr.replace('.', '').isdigit() else 0
        rr = float(rr)
        
        if rr > 30 or rr < 8:
            score += 4
        elif rr > 25 or rr < 12:
            score += 2
        
        # Heart Rate
        hr = data.get('heart_rate', 0)
        if isinstance(hr, str):
            hr = float(hr) if hr.replace('.', '').isdigit() else 0
        hr = float(hr)
        
        if hr > 140 or hr < 40:
            score += 4
        elif hr > 120 or hr < 50:
            score += 2
        
        # Oxygen Saturation
        spo2 = data.get('oxygen_saturation', 100)
        if isinstance(spo2, str):
            spo2 = float(spo2) if spo2.replace('.', '').isdigit() else 100
        spo2 = float(spo2)
        
        if spo2 < 85:
            score += 4
        elif spo2 < 92:
            score += 2
        
        # Temperature
        temp = data.get('temperature', 37)
        if isinstance(temp, str):
            temp = float(temp) if temp.replace('.', '').isdigit() else 37
        temp = float(temp)
        
        if temp > 39.5 or temp < 35:
            score += 3
        elif temp > 38.5:
            score += 1
        
        # Blood Pressure
        sys = data.get('blood_pressure_systolic', 0)
        if isinstance(sys, str):
            sys = int(sys) if sys.isdigit() else 0
        sys = int(sys)
        
        if sys > 180 or sys < 90:
            score += 4
        elif sys > 160:
            score += 2
        
        # Consciousness Level
        consciousness = data.get('consciousness_level', 'alert')
        if consciousness == 'unresponsive':
            score += 4
        elif consciousness == 'confused':
            score += 2
        
        # Pain Score
        pain = data.get('pain_score', 0)
        if isinstance(pain, str):
            pain = int(pain) if pain.isdigit() else 0
        pain = int(pain)
        
        if pain > 8:
            score += 2
        elif pain > 6:
            score += 1
        
        # Determine triage level
        if score >= 15:
            return 'Resuscitation', 'Red', score
        elif score >= 10:
            return 'Emergency', 'Orange', score
        elif score >= 5:
            return 'Urgent', 'Yellow', score
        elif score >= 2:
            return 'Semi-Urgent', 'Green', score
        else:
            return 'Non-Urgent', 'Blue', score
    
    def get_triage_by_patient(self, patient_id: str) -> List[Dict]:
        """Get all triage records for a patient"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM triage_records WHERE patient_id = ? 
                ORDER BY created_at DESC
            ''', (patient_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            triage_records = []
            for row in rows:
                triage_records.append({
                    'id': row[0],
                    'patient_id': row[1],
                    'doctor_id': row[2],
                    'triage_level': row[3],
                    'triage_color': row[4],
                    'triage_score': row[5],
                    'respiratory_rate': row[6],
                    'heart_rate': row[7],
                    'oxygen_saturation': row[8],
                    'temperature': row[9],
                    'blood_pressure_systolic': row[10],
                    'blood_pressure_diastolic': row[11],
                    'consciousness_level': row[12],
                    'pain_score': row[13],
                    'chief_complaint': row[14],
                    'symptoms': row[15],
                    'notes': row[16],
                    'created_at': row[17],
                    'updated_at': row[18]
                })
            
            return triage_records
            
        except Exception as e:
            print(f"Error getting triage records: {e}")
            return []
    
    def get_triage_by_doctor(self, doctor_id: str) -> List[Dict]:
        """Get all triage records for a doctor"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT t.*, p.name as patient_name, p.rhd_status as patient_rhd_status
                FROM triage_records t
                JOIN patients p ON t.patient_id = p.id
                WHERE t.doctor_id = ? 
                ORDER BY 
                    CASE t.triage_color
                        WHEN 'Red' THEN 1
                        WHEN 'Orange' THEN 2
                        WHEN 'Yellow' THEN 3
                        WHEN 'Green' THEN 4
                        WHEN 'Blue' THEN 5
                    END,
                    t.created_at DESC
            ''', (doctor_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            triage_records = []
            for row in rows:
                triage_records.append({
                    'id': row[0],
                    'patient_id': row[1],
                    'doctor_id': row[2],
                    'triage_level': row[3],
                    'triage_color': row[4],
                    'triage_score': row[5],
                    'respiratory_rate': row[6],
                    'heart_rate': row[7],
                    'oxygen_saturation': row[8],
                    'temperature': row[9],
                    'blood_pressure_systolic': row[10],
                    'blood_pressure_diastolic': row[11],
                    'consciousness_level': row[12],
                    'pain_score': row[13],
                    'chief_complaint': row[14],
                    'symptoms': row[15],
                    'notes': row[16],
                    'created_at': row[17],
                    'updated_at': row[18],
                    'patient_name': row[19] if len(row) > 19 else None,
                    'patient_rhd_status': row[20] if len(row) > 20 else 'unknown'
                })
            
            return triage_records
            
        except Exception as e:
            print(f"Error getting triage records: {e}")
            return []
    
    # ============ HEART SOUND RECORDING METHODS ============
    
    def save_heart_sound_recording(self, doctor_id: str, data: Dict) -> Optional[str]:
        """Save a heart sound recording to the database"""
        try:
            recording_id = str(uuid.uuid4())[:8]
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Handle file data if present
            file_data = data.get('file')
            file_name = None
            file_path = None
            file_url = data.get('file_url')
            
            if file_data:
                # If it's a file object from Flask
                if hasattr(file_data, 'filename'):
                    file_name = file_data.filename
                elif isinstance(file_data, str):
                    file_name = file_data
                    file_path = file_data
            
            # Handle recording date
            recording_date = data.get('recording_date')
            if not recording_date:
                recording_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
                INSERT INTO heart_sound_recordings (
                    id, patient_id, doctor_id, file_name, file_path, file_url,
                    prediction, confidence, recording_date, notes,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (
                recording_id,
                data.get('patient_id'),
                doctor_id,
                file_name,
                file_path,
                file_url,
                data.get('prediction'),
                data.get('confidence'),
                recording_date,
                data.get('notes', '')
            ))
            
            conn.commit()
            conn.close()
            return recording_id
            
        except Exception as e:
            print(f"❌ Error saving recording: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_recordings_by_patient(self, patient_id: str) -> List[Dict]:
        """Get all recordings for a patient"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    id, patient_id, doctor_id, file_name, file_path, file_url,
                    prediction, confidence, recording_date, notes,
                    created_at, updated_at
                FROM heart_sound_recordings
                WHERE patient_id = ?
                ORDER BY created_at DESC
            ''', (patient_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            recordings = []
            for row in rows:
                recordings.append({
                    'id': row[0],
                    'patient_id': row[1],
                    'doctor_id': row[2],
                    'file_name': row[3],
                    'file_path': row[4],
                    'file_url': row[5],
                    'prediction': row[6],
                    'confidence': row[7],
                    'recording_date': row[8],
                    'notes': row[9],
                    'created_at': row[10],
                    'updated_at': row[11]
                })
            
            return recordings
            
        except Exception as e:
            print(f"❌ Error fetching recordings: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    # ============ IOT DEVICE METHODS ============
    
    def register_iot_device(self, doctor_id: str, data: Dict) -> Optional[str]:
        """Register an IoT stethoscope device"""
        try:
            device_id = str(uuid.uuid4())[:8]
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO iot_devices (
                    id, doctor_id, device_name, device_type, ip_address, mac_address, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                device_id,
                doctor_id,
                data.get('device_name'),
                data.get('device_type', 'stethoscope'),
                data.get('ip_address'),
                data.get('mac_address'),
                'offline'
            ))
            
            conn.commit()
            conn.close()
            return device_id
            
        except Exception as e:
            print(f"Error registering device: {e}")
            return None
    
    def update_device_status(self, device_id: str, status: str) -> bool:
        """Update IoT device status"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE iot_devices 
                SET status = ?, last_connected = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, device_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error updating device status: {e}")
            return False
    
    def get_doctor_devices(self, doctor_id: str) -> List[Dict]:
        """Get all IoT devices for a doctor"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM iot_devices WHERE doctor_id = ?
            ''', (doctor_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            devices = []
            for row in rows:
                devices.append({
                    'id': row[0],
                    'doctor_id': row[1],
                    'device_name': row[2],
                    'device_type': row[3],
                    'ip_address': row[4],
                    'mac_address': row[5],
                    'status': row[6],
                    'last_connected': row[7],
                    'created_at': row[8]
                })
            
            return devices
            
        except Exception as e:
            print(f"Error getting devices: {e}")
            return []
    
    # ============ RHD STATS & AUTOMATION METHODS ============
    
    def update_patient_rhd_from_prediction(self, patient_id: str, prediction: str, confidence: float) -> bool:
        """
        Automatically update patient RHD status based on ML prediction
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Determine RHD status from prediction
            if prediction == 'RHD':
                if confidence > 0.7:
                    rhd_status = 'suspected'
                    rhd_recommendation = 'High risk - Refer to cardiologist'
                    follow_up_days = 30
                elif confidence > 0.4:
                    rhd_status = 'suspected'
                    rhd_recommendation = 'Moderate risk - Further monitoring required'
                    follow_up_days = 90
                else:
                    rhd_status = 'suspected'
                    rhd_recommendation = 'Low risk - Monitor symptoms'
                    follow_up_days = 180
            else:
                rhd_status = 'none'
                rhd_recommendation = 'No RHD detected'
                follow_up_days = 365
            
            # Update patient
            cursor.execute('''
                UPDATE patients 
                SET rhd_status = ?,
                    rhd_notes = ?,
                    last_rhd_assessment = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (rhd_status, rhd_recommendation, patient_id))
            
            # Create follow-up reminder if RHD suspected
            if rhd_status == 'suspected':
                reminder_id = str(uuid.uuid4())[:8]
                cursor.execute('''
                    INSERT INTO follow_up_reminders (
                        id, patient_id, recommended_days, reason, created_at
                    ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (reminder_id, patient_id, follow_up_days, rhd_recommendation))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error updating RHD status: {e}")
            return False
    
    def get_rhd_stats(self, doctor_id: str) -> Dict:
        """
        Get RHD statistics for dashboard
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Total patients
            cursor.execute('SELECT COUNT(*) FROM patients WHERE doctor_id = ?', (doctor_id,))
            total_patients = cursor.fetchone()[0]
            
            # RHD breakdown
            cursor.execute('''
                SELECT rhd_status, COUNT(*) 
                FROM patients 
                WHERE doctor_id = ? 
                GROUP BY rhd_status
            ''', (doctor_id,))
            rhd_breakdown = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Age distribution of RHD cases
            cursor.execute('''
                SELECT 
                    CASE 
                        WHEN age < 15 THEN '5-14'
                        WHEN age < 25 THEN '15-24'
                        WHEN age < 35 THEN '25-34'
                        WHEN age < 45 THEN '35-44'
                        ELSE '45+'
                    END as age_group,
                    COUNT(*) as count
                FROM patients 
                WHERE doctor_id = ? AND rhd_status IN ('suspected', 'confirmed')
                GROUP BY age_group
            ''', (doctor_id,))
            age_distribution = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Recent RHD cases
            cursor.execute('''
                SELECT p.name, p.age, p.rhd_status, p.last_rhd_assessment,
                       t.triage_color
                FROM patients p
                LEFT JOIN triage_records t ON p.id = t.patient_id
                WHERE p.doctor_id = ? AND p.rhd_status IN ('suspected', 'confirmed')
                ORDER BY p.last_rhd_assessment DESC
                LIMIT 10
            ''', (doctor_id,))
            recent_cases = []
            for row in cursor.fetchall():
                recent_cases.append({
                    'name': row[0],
                    'age': row[1],
                    'status': row[2],
                    'assessment_date': row[3],
                    'triage_color': row[4]
                })
            
            conn.close()
            
            return {
                'total_screened': total_patients,
                'rhd_suspected': rhd_breakdown.get('suspected', 0),
                'rhd_confirmed': rhd_breakdown.get('confirmed', 0),
                'rhd_none': rhd_breakdown.get('none', 0),
                'rhd_unknown': rhd_breakdown.get('unknown', 0),
                'rhd_prevalence': ((rhd_breakdown.get('suspected', 0) + rhd_breakdown.get('confirmed', 0)) / total_patients * 100) if total_patients > 0 else 0,
                'age_distribution': age_distribution,
                'recent_cases': recent_cases
            }
            
        except Exception as e:
            print(f"Error getting RHD stats: {e}")
            return {}

# Global database instance
db = DoctorDatabase()