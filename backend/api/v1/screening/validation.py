from flask import Blueprint, request, jsonify
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

validation_bp = Blueprint('validation', __name__)

# =========================
# VALIDATION ENDPOINT
# =========================
@validation_bp.route('/validate', methods=['POST', 'OPTIONS'])
def validate():
    """Validate heart sound recording"""
    try:
        # Get the uploaded file and data
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
        
        # If JSON data is sent instead
        data = request.json
        if data:
            return jsonify({
                'success': True,
                'message': 'Validation successful',
                'data': data
            })
        
        return jsonify({'error': 'No data or file provided'}), 400
        
    except Exception as e:
        print(f"❌ Validation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# =========================
# PREDICTION ENDPOINT
# =========================
@validation_bp.route('/predict', methods=['POST', 'OPTIONS'])
def predict():
    """Predict heart condition from recording"""
    try:
        # Get the uploaded file and data
        if request.files and 'file' in request.files:
            file = request.files.get('file')
            if not file:
                return jsonify({'error': 'No file provided'}), 400
            
            # Here you would process the file and make predictions
            # For now, return a mock prediction
            return jsonify({
                'success': True,
                'prediction': {
                    'condition': 'Normal',
                    'confidence': 0.95,
                    'recommendations': ['No action needed', 'Continue monitoring']
                },
                'file_name': file.filename
            })
        
        # If JSON data is sent instead
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
        
        return jsonify({'error': 'No data or file provided'}), 400
        
    except Exception as e:
        print(f"❌ Prediction error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# =========================
# HEALTH CHECK FOR SCREENING
# =========================
@validation_bp.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'screening/validation'
    })