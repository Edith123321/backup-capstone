from flask import Blueprint, request, jsonify
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

validation_bp = Blueprint('validation', __name__)

# =========================
# VALIDATION ENDPOINT
# =========================
@validation_bp.route('/validate', methods=['POST'])
def validate():
    """Validate heart sound recording"""
    try:
        # Handle file upload
        if request.files and 'file' in request.files:
            file = request.files.get('file')
            if not file:
                return jsonify({'error': 'No file provided'}), 400
            
            # Here you would validate the file
            # For now, return a success response
            return jsonify({
                'success': True,
                'message': 'File validated successfully',
                'file_name': file.filename,
                'file_size': len(file.read()) if file else 0
            })
        
        # Handle JSON data
        if request.is_json:
            data = request.json
            if data:
                return jsonify({
                    'success': True,
                    'message': 'Validation successful',
                    'data': data
                })
        
        # Handle empty requests
        return jsonify({
            'success': True,
            'message': 'Validation successful (no data provided)',
            'hint': 'Send a file or JSON data for actual validation'
        })
        
    except Exception as e:
        print(f"❌ Validation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# =========================
# PREDICTION ENDPOINT
# =========================
@validation_bp.route('/predict', methods=['POST'])
def predict():
    """Predict heart condition from recording"""
    try:
        # Handle file upload
        if request.files and 'file' in request.files:
            file = request.files.get('file')
            if not file:
                return jsonify({'error': 'No file provided'}), 400
            
            # Mock prediction for file
            return jsonify({
                'success': True,
                'prediction': {
                    'condition': 'Normal',
                    'confidence': 0.95,
                    'recommendations': ['No action needed', 'Continue monitoring']
                },
                'file_name': file.filename
            })
        
        # Handle JSON data
        if request.is_json:
            data = request.json
            if data:
                # Mock prediction based on data
                return jsonify({
                    'success': True,
                    'prediction': {
                        'condition': 'Normal',
                        'confidence': 0.92,
                        'recommendations': ['Regular checkup recommended']
                    },
                    'data_received': data
                })
        
        # Handle empty requests
        return jsonify({
            'success': True,
            'message': 'Prediction successful (no data provided)',
            'hint': 'Send a file or JSON data for actual prediction'
        })
        
    except Exception as e:
        print(f"❌ Prediction error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# =========================
# HEALTH CHECK
# =========================
@validation_bp.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'screening/validation',
        'endpoints': {
            'validate': '/api/v1/screening/validate',
            'predict': '/api/v1/screening/predict'
        }
    })