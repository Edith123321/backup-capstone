# Example usage in backend/services/prognosis.py

from services.markov_model import risk_calculator, markov_model

def get_patient_prognosis(patient_id: str, current_grade: int, clinical_data: Dict) -> Dict:
    """
    Get comprehensive prognosis for a patient.
    """
    # Prepare clinical data
    data = {
        'current_grade': current_grade,
        'age': clinical_data.get('age', 30),
        'gender': clinical_data.get('gender', 'male'),
        'risk_factors': clinical_data.get('risk_factors', []),
        'treatment': clinical_data.get('treatment', 'none'),
        'history': clinical_data.get('history', [])
    }
    
    # Calculate risk
    result = risk_calculator.calculate_risk(patient_id, data)
    
    # Get longitudinal prediction
    prediction = risk_calculator.get_longitudinal_prediction(patient_id, months=24)
    
    return {
        'risk_assessment': result,
        'longitudinal_prediction': prediction,
        'recommendations': result['prognosis']['recommendations'],
        'timestamp': datetime.now().isoformat()
    }

# Example API endpoint usage
def prognosis_endpoint(patient_id: str):
    """
    Flask endpoint example
    """
    # Get patient data from database
    patient = db.get_patient_by_id(patient_id)
    recordings = db.get_recordings_by_patient(patient_id)
    
    if not patient or not recordings:
        return {'error': 'Patient or recordings not found'}
    
    # Determine current grade from latest recording
    latest = recordings[0]
    current_grade = latest.get('severity_grade', 0)
    
    # Clinical data from patient record
    clinical_data = {
        'age': patient.get('age', 30),
        'gender': patient.get('gender', 'male'),
        'risk_factors': ['rheumatic_fever_history'] if patient.get('rhd_status') == 'suspected' else [],
        'treatment': 'none'
    }
    
    # Get prognosis
    result = get_patient_prognosis(patient_id, current_grade, clinical_data)
    
    # Save prognosis to database
    db.save_prognosis(patient_id, result)
    
    return result