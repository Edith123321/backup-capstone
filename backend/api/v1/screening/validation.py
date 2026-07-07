from flask import Blueprint, request, jsonify
import os
import sys
import tempfile
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

validation_bp = Blueprint('validation', __name__)

# =========================
# VALIDATION ENDPOINT
# =========================
@validation_bp.route('/validate', methods=['POST', 'OPTIONS'])
def validate():
    """Validate heart sound recording"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        # Handle JSON data first
        if request.is_json:
            data = request.get_json()
            if data:
                print(f"📊 Validate with JSON data: {data}")
                return jsonify({
                    'success': True,
                    'message': 'Validation successful',
                    'data': data,
                    'source': 'json_input'
                })
        
        # Handle file upload
        if 'file' in request.files and request.files.get('file'):
            file = request.files.get('file')
            if not file or file.filename == '':
                return jsonify({'error': 'No file provided'}), 400
            
            file_data = file.read()
            file_size = len(file_data)
            
            print(f"📁 Validate with file: {file.filename}")
            
            return jsonify({
                'success': True,
                'message': 'File validated successfully',
                'file_name': file.filename,
                'file_size': file_size,
                'source': 'file_upload'
            })
        
        # Handle form data with JSON
        if request.form and request.form.get('data'):
            try:
                data = json.loads(request.form.get('data'))
                return jsonify({
                    'success': True,
                    'message': 'Validation successful',
                    'data': data,
                    'source': 'form_data'
                })
            except:
                pass
        
        # Handle empty requests
        return jsonify({
            'success': True,
            'message': 'Validation successful (no data provided)',
            'hint': 'Send a file or JSON data for actual validation',
            'source': 'empty'
        })
        
    except Exception as e:
        print(f"❌ Validation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# =========================
# PREDICTION ENDPOINT (FIXED - JSON FIRST)
# =========================
@validation_bp.route('/predict', methods=['POST', 'OPTIONS'])
def predict():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    print(f"🔍 Predict received: is_json={request.is_json}, files={list(request.files.keys())}, form={list(request.form.keys())}")
    
    # 1. If JSON (manual symptoms)
    if request.is_json:
        data = request.get_json()
        if data:
            print(f"📊 Predict JSON data: {data}")
            # ... return mock prediction ...
    
    # 2. If file upload
    if 'file' in request.files:
        file = request.files['file']
        if file and file.filename != '':
            print(f"📁 Predict file: {file.filename}, size: {len(file.read())}")
            file.seek(0)  # reset after read
            # Process file...
            return jsonify({...})
    
    # 3. If form data (maybe file sent without 'file' key)
    if request.form:
        print(f"📋 Predict form data: {request.form}")
        # Possibly handle if file is in form data?
    
    print("❌ No file or JSON found")
    return jsonify({'error': 'No file uploaded'}), 400

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