# backend/app.py
from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
from flask_session import Session
from dotenv import load_dotenv
import os
import sys
import logging
from datetime import datetime
import tempfile

# Load environment variables
load_dotenv()

# =========================
# PATH CONFIGURATION
# =========================
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# =========================
# LOGGING CONFIGURATION
# =========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('saka.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# =========================
# IMPORT BLUEPRINTS
# =========================
from api.v1.screening.heart_sound import heart_sound_bp
from api.v1.screening.database_routes import database_bp
from api.v1.screening.validation import validation_bp
from api.v1.screening.encounter_routes import encounter_bp
from api.v1.auth.google_auth import auth_bp
from api.v1.auth.test_auth import test_auth_bp

# =========================
# IMPORT SERVICES
# =========================
try:
    from services.database import db
    from services.severity_grading import severity_grader
    from services.markov_model import risk_calculator
    from services.report_generator import report_generator
    logger.info("✅ All services loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Some services failed to import: {e}")

# =========================
# APP INIT
# =========================
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_TYPE'] = 'filesystem'
# Store session files OUTSIDE the import path. Flask-Session's default
# ('flask_session/' in the working dir) shadows the installed flask_session
# package when a gunicorn worker restarts and re-imports the app, causing
# "cannot import name 'Session' from 'flask_session'". A temp dir avoids it.
app.config['SESSION_FILE_DIR'] = os.environ.get(
    'SESSION_FILE_DIR', os.path.join(tempfile.gettempdir(), 'saka_sessions'))
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
app.config['REPORT_FOLDER'] = os.path.join(backend_dir, 'reports')

# Create report folder if it doesn't exist
if not os.path.exists(app.config['REPORT_FOLDER']):
    os.makedirs(app.config['REPORT_FOLDER'])

Session(app)

# =========================
# CORS CONFIGURATION
# =========================
allowed_origins = [
    "http://localhost:5173",
    "http://localhost:3000", 
    "http://localhost:5000",
    "http://localhost:5001",
    "https://backup-capstone-mbq6.onrender.com",
    "https://capstone-be-yxzd.onrender.com",
]

CORS(
    app,
    origins=allowed_origins,
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept"],
    expose_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    max_age=3600
)

# =========================
# BLUEPRINT REGISTRATION
# =========================
# Screening endpoints
app.register_blueprint(heart_sound_bp, url_prefix="/api/v1/screening")
app.register_blueprint(validation_bp, url_prefix="/api/v1/screening")
app.register_blueprint(encounter_bp, url_prefix="/api/v1")

# Database endpoints
app.register_blueprint(database_bp, url_prefix="/api/v1/database")

# Authentication endpoints
app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
app.register_blueprint(test_auth_bp, url_prefix="/api/v1/auth/test")

logger.info("✅ SAKA Blueprints registered successfully")

# =========================
# ROOT - API Information
# =========================
@app.route("/")
def index():
    return jsonify({
        "name": "SAKA Clinical Decision Support System",
        "version": "2.0.0",
        "status": "running",
        "features": {
            "ai_screening": True,
            "triage_system": True,
            "severity_grading": True,
            "prognostic_risk": True,
            "report_generation": True,
            "offline_sync": True,
            "iot_integration": True
        },
        "endpoints": {
            "auth": {
                "login": "/api/v1/auth/google/login",
                "callback": "/api/v1/auth/google/callback",
                "logout": "/api/v1/auth/logout",
                "debug": "/api/v1/auth/debug"
            },
            "screening": {
                "predict": "/api/v1/screening/predict",
                "validate": "/api/v1/screening/validate",
                "health": "/api/v1/screening/health",
                "recordings": "/api/v1/screening/recordings/<patient_id>",
                "history": "/api/v1/screening/history/<patient_id>"
            },
            "database": {
                "patients": "/api/v1/database/patients",
                "patient": "/api/v1/database/patients/<patient_id>",
                "triage": "/api/v1/database/triage",
                "recordings": "/api/v1/database/recordings",
                "devices": "/api/v1/database/devices",
                "rhd_summary": "/api/v1/database/patients/rhd-summary",
                "severity_history": "/api/v1/database/severity/history/<patient_id>",
                "severity_trend": "/api/v1/database/severity/trend/<patient_id>"
            },
            "prognosis": {
                "risk_score": "/api/v1/prognosis/risk/<patient_id>",
                "prediction": "/api/v1/prognosis/predict/<patient_id>",
                "trend": "/api/v1/prognosis/trend/<patient_id>"
            },
            "reports": {
                "generate": "/api/v1/reports/generate",
                "download": "/api/v1/reports/download/<filename>"
            },
            "system": {
                "health": "/health",
                "cors_test": "/api/test-cors",
                "offline_status": "/api/offline/status"
            }
        }
    })

# =========================
# HEALTH CHECK
# =========================
@app.route("/health")
def health():
    """System health check"""
    # Reflect the real classifier state rather than a flag that is never set.
    try:
        from api.v1.screening.heart_sound import classifier as _clf
        ai_model_status = "loaded" if _clf is not None else "not_loaded"
    except Exception:
        ai_model_status = "unavailable"

    services_status = {
        "database": "healthy" if db else "unavailable",
        "ai_model": ai_model_status,
        "severity_grading": "available" if severity_grader else "unavailable",
        "report_generator": "available" if report_generator else "unavailable"
    }
    
    return jsonify({
        "status": "healthy",
        "service": "SAKA CDSS",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "services": services_status,
        "environment": os.environ.get("FLASK_ENV", "production")
    })

# =========================
# CORS TEST ENDPOINT
# =========================
@app.route("/api/test-cors")
def test_cors():
    """Test endpoint to verify CORS is working"""
    return jsonify({
        "success": True,
        "message": "CORS is working!",
        "origin": request.headers.get('Origin'),
        "method": request.method
    })

# =========================
# OFFLINE STATUS ENDPOINT
# =========================
@app.route("/api/offline/status")
def offline_status():
    """Get offline sync status"""
    try:
        # Try to import offline_sync
        try:
            from services.offline_sync import get_sync_status
            status = get_sync_status()
            return jsonify({
                "success": True,
                "status": status
            })
        except ImportError:
            # Fallback status if offline_sync not available
            return jsonify({
                "success": True,
                "status": {
                    "queue_size": 0,
                    "pending_items": 0,
                    "last_sync": None,
                    "is_online": True,
                    "message": "Offline sync service not configured"
                }
            })
    except Exception as e:
        logger.error(f"Error getting offline status: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# =========================
# PROGNOSIS ENDPOINTS
# =========================
@app.route("/api/v1/prognosis/risk/<patient_id>", methods=['GET', 'OPTIONS'])
def get_prognostic_risk(patient_id):
    """Get prognostic risk score for a patient"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        # Get patient data
        patient = db.get_patient_by_id(patient_id)
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        # Get latest recording for severity
        recordings = db.get_recordings_by_patient(patient_id)
        if not recordings:
            return jsonify({'error': 'No recordings found for patient'}), 404
        
        # Determine current grade
        latest = recordings[0]
        current_grade = latest.get('severity_grade', 0)
        
        # Get clinical data
        clinical_data = {
            'current_grade': current_grade,
            'age': patient.get('age', 30),
            'gender': patient.get('gender', 'male'),
            'risk_factors': ['history_of_rhd'] if patient.get('rhd_status') == 'suspected' else [],
            'treatment': 'none'
        }
        
        # Calculate risk
        result = risk_calculator.calculate_risk(patient_id, clinical_data)
        
        return jsonify({
            'success': True,
            'patient_id': patient_id,
            'prognosis': result
        })
        
    except Exception as e:
        logger.error(f"Error calculating prognostic risk: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route("/api/v1/prognosis/predict/<patient_id>", methods=['GET', 'OPTIONS'])
def get_longitudinal_prediction(patient_id):
    """Get longitudinal prediction for a patient"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        months = request.args.get('months', 24, type=int)
        
        result = risk_calculator.get_longitudinal_prediction(patient_id, months=months)
        
        return jsonify({
            'success': True,
            'patient_id': patient_id,
            'prediction': result
        })
        
    except Exception as e:
        logger.error(f"Error getting longitudinal prediction: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route("/api/v1/prognosis/trend/<patient_id>", methods=['GET', 'OPTIONS'])
def get_prognosis_trend(patient_id):
    """Get prognostic trend analysis"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        # Use public method to get history
        history = risk_calculator._get_grade_history(patient_id)
        
        if not history:
            return jsonify({
                'success': True,
                'trend': 'Insufficient data',
                'message': 'Need at least 2 assessments for trend analysis'
            })
        
        return jsonify({
            'success': True,
            'patient_id': patient_id,
            'history': history,
            'total_assessments': len(history)
        })
        
    except Exception as e:
        logger.error(f"Error getting prognosis trend: {str(e)}")
        return jsonify({'error': str(e)}), 500

# =========================
# SEVERITY ENDPOINTS
# =========================
@app.route("/api/v1/severity/grade", methods=['POST', 'OPTIONS'])
def get_severity_grade():
    """Get severity grade for a prediction"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        data = request.json
        prediction = data.get('prediction')
        confidence = data.get('confidence', 0)
        auscultation_point = data.get('auscultation_point')
        clinical_data = data.get('clinical_data', {})
        
        if not prediction:
            return jsonify({'error': 'Prediction is required'}), 400
        
        result = severity_grader.grade_from_prediction(
            prediction=prediction,
            confidence=confidence,
            auscultation_point=auscultation_point,
            clinical_data=clinical_data
        )
        
        return jsonify({
            'success': True,
            'severity': result.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error getting severity grade: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route("/api/v1/severity/history/<patient_id>", methods=['GET', 'OPTIONS'])
def get_severity_history(patient_id):
    """Get severity history for a patient"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        limit = request.args.get('limit', 20, type=int)
        history = severity_grader.get_severity_history(patient_id, limit=limit)
        
        return jsonify({
            'success': True,
            'patient_id': patient_id,
            'history': history,
            'count': len(history)
        })
        
    except Exception as e:
        logger.error(f"Error getting severity history: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route("/api/v1/severity/trend/<patient_id>", methods=['GET', 'OPTIONS'])
def get_severity_trend(patient_id):
    """Get severity trend analysis"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        trend = severity_grader.get_severity_trend(patient_id)
        
        return jsonify({
            'success': True,
            'patient_id': patient_id,
            'trend': trend
        })
        
    except Exception as e:
        logger.error(f"Error getting severity trend: {str(e)}")
        return jsonify({'error': str(e)}), 500

# =========================
# REPORT ENDPOINTS
# =========================
@app.route("/api/v1/reports/generate", methods=['POST', 'OPTIONS'])
def generate_report():
    """Generate a PDF report for a patient"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        data = request.json
        patient_id = data.get('patient_id')
        
        if not patient_id:
            return jsonify({'error': 'Patient ID is required'}), 400
        
        # Get patient data
        patient = db.get_patient_by_id(patient_id)
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        # Get recordings
        recordings = db.get_recordings_by_patient(patient_id)
        triage = db.get_triage_by_patient(patient_id)
        
        # Get doctor info
        doctor = db.get_doctor(patient.get('doctor_id'))
        
        # Get severity history
        severity_history = severity_grader.get_severity_history(patient_id, limit=10)
        
        # Get prognostic risk
        clinical_data = {
            'current_grade': recordings[0].get('severity_grade', 0) if recordings else 0,
            'age': patient.get('age', 30),
            'gender': patient.get('gender', 'male'),
            'risk_factors': [],
            'treatment': 'none'
        }
        risk_result = risk_calculator.calculate_risk(patient_id, clinical_data)
        
        # Prepare report data
        report_data = {
            'patient_name': patient.get('name', ''),
            'patient_age': patient.get('age', 0),
            'patient_gender': patient.get('gender', ''),
            'patient_contact': patient.get('contact', ''),
            'patient_address': patient.get('address', ''),
            'doctor_id': patient.get('doctor_id', ''),
            'doctor_name': doctor.get('name', '') if doctor else '',
            'doctor_hospital': doctor.get('hospital', 'Saka RHD Detection Center') if doctor else 'Saka RHD Detection Center',
            'assessment_date': datetime.now().strftime('%Y-%m-%d'),
            'triage_color': triage[0].get('triage_color') if triage else None,
            'triage_level': triage[0].get('triage_level') if triage else None,
            'triage_score': triage[0].get('triage_score') if triage else None,
            'prediction': recordings[0].get('prediction') if recordings else None,
            'confidence': recordings[0].get('confidence') if recordings else None,
            'severity_grade': recordings[0].get('severity_grade') if recordings else None,
            'severity_label': recordings[0].get('severity_label') if recordings else None,
            'auscultation_point': recordings[0].get('auscultation_point') if recordings else None,
            'auscultation_label': recordings[0].get('auscultation_label') if recordings else None,
            'recordings': recordings[:5],
            'symptoms': data.get('symptoms', []),
            'medical_history': patient.get('medical_history', ''),
            'clinical_notes': data.get('clinical_notes', ''),
            'risk_score': risk_result.get('prognosis', {}).get('risk_score') if risk_result else None,
            'risk_level': risk_result.get('prognosis', {}).get('risk_level') if risk_result else None,
            'prognosis_trend': risk_result.get('trend', {}).get('direction') if risk_result else None,
            'recommendations': data.get('recommendations', [
                'Complete echocardiography',
                'Cardiology consultation within 30 days',
                'Continue monitoring symptoms'
            ]),
            'referral_priority': data.get('referral_priority', 'Routine'),
            'follow_up_days': data.get('follow_up_days', 90)
        }
        
        # Generate report
        from services.report_generator import generate_patient_report
        result = generate_patient_report(patient_id, report_data)
        
        if result['success']:
            return jsonify({
                'success': True,
                'report_id': result['report_id'],
                'report_url': result['url'],
                'filename': result['filename'],
                'generated_at': result['generated_at']
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to generate report')
            }), 500
        
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route("/api/v1/reports/download/<filename>", methods=['GET', 'OPTIONS'])
def download_report(filename):
    """Download a generated report"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        report_path = os.path.join(app.config['REPORT_FOLDER'], filename)
        
        if not os.path.exists(report_path):
            return jsonify({'error': 'Report not found'}), 404
        
        return send_file(
            report_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"Error downloading report: {str(e)}")
        return jsonify({'error': str(e)}), 500

# =========================
# IOT DEVICE ENDPOINTS
# =========================
@app.route("/api/v1/iot/status", methods=['GET', 'OPTIONS'])
def get_iot_status():
    """Get IoT device connection status"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        doctor_id = request.args.get('doctor_id')
        device_id = request.args.get('device_id')
        
        if device_id:
            # Get specific device by ID
            device = db.get_device_by_id(device_id)
            devices = [device] if device else []
        elif doctor_id:
            # Get all devices for a doctor
            devices = db.get_doctor_devices(doctor_id)
        else:
            return jsonify({'error': 'doctor_id or device_id required'}), 400
        
        return jsonify({
            'success': True,
            'devices': devices,
            'online_count': sum(1 for d in devices if d.get('status') == 'online'),
            'total_count': len(devices)
        })
        
    except Exception as e:
        logger.error(f"Error getting IoT status: {str(e)}")
        return jsonify({'error': str(e)}), 500

# =========================
# RHD SUMMARY DASHBOARD ENDPOINTS
# =========================
@app.route("/api/v1/dashboard/rhd-summary", methods=['GET', 'OPTIONS'])
def get_dashboard_rhd_summary():
    """Get RHD summary for dashboard"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        doctor_id = request.args.get('doctor_id')
        if not doctor_id:
            return jsonify({'error': 'doctor_id required'}), 400
        
        # Get RHD stats from database
        stats = db.get_rhd_stats(doctor_id)
        
        # Get severity breakdown
        severity_breakdown = {
            'grade_0': 0,
            'grade_1': 0,
            'grade_2': 0
        }
        
        patients = db.get_patients_by_doctor(doctor_id)
        for patient in patients:
            recordings = db.get_recordings_by_patient(patient['id'])
            if recordings:
                latest = recordings[0]
                grade = latest.get('severity_grade', 0)
                if grade in severity_breakdown:
                    severity_breakdown[f'grade_{grade}'] += 1
        
        return jsonify({
            'success': True,
            'summary': {
                'total_patients': stats.get('total_screened', 0),
                'rhd_suspected': stats.get('rhd_suspected', 0),
                'rhd_confirmed': stats.get('rhd_confirmed', 0),
                'rhd_prevalence': stats.get('rhd_prevalence', 0),
                'severity_breakdown': severity_breakdown,
                'recent_cases': stats.get('recent_cases', [])
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {str(e)}")
        return jsonify({'error': str(e)}), 500

# =========================
# ERROR HANDLERS
# =========================
@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "Endpoint not found",
        "hint": "Check the / endpoint for available routes",
        "timestamp": datetime.now().isoformat()
    }), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {str(e)}")
    return jsonify({
        "error": "Internal server error",
        "message": str(e) if app.debug else "An error occurred. Please try again.",
        "timestamp": datetime.now().isoformat()
    }), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({
        "error": "File too large",
        "message": "Maximum file size is 50MB",
        "timestamp": datetime.now().isoformat()
    }), 413

# =========================
# REQUEST LOGGING
# =========================
@app.before_request
def log_request():
    """Log all requests"""
    if request.method != 'OPTIONS':  # Skip OPTIONS for cleaner logs
        logger.info(f"📥 {request.method} {request.path} - {request.remote_addr}")

@app.after_request
def log_response(response):
    """Log all responses"""
    if request.method != 'OPTIONS':  # Skip OPTIONS for cleaner logs
        logger.info(f"📤 {request.method} {request.path} - {response.status_code}")
    return response

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    
    logger.info(f"🚀 Starting SAKA CDSS v2.0.0 on port {port}")
    logger.info(f"🔧 Debug mode: {debug}")
    logger.info(f"📂 Report folder: {app.config['REPORT_FOLDER']}")
    
    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug,
        threaded=True
    )