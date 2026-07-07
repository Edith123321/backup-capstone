# Example usage in backend/heart_sound.py or any prediction endpoint

from services.severity_grading import severity_grader, SeverityResult

def predict_with_severity(file_path, patient_id, doctor_id, auscultation_point=None, clinical_data=None):
    """
    Get prediction with severity grading
    """
    # Get AI prediction
    result = classifier.predict(file_path)
    
    if result:
        prediction = result['class']  # 'Normal' or 'RHD'
        confidence = result['confidence']
        
        # Grade the severity
        severity = severity_grader.grade_from_prediction(
            prediction=prediction,
            confidence=confidence,
            auscultation_point=auscultation_point,
            clinical_data=clinical_data
        )
        
        # Track for longitudinal analysis
        severity_grader.track_severity_history(patient_id, severity)
        
        # Get prognostic risk
        prognosis = severity_grader.calculate_prognostic_risk(patient_id)
        
        return {
            'prediction': prediction,
            'confidence': confidence,
            'severity': severity.to_dict(),
            'prognosis': prognosis,
            'recommendation': severity.recommendation
        }
    
    return None