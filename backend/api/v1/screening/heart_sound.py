# backend/api/v1/screening/heart_sound.py
from flask import request, jsonify, Blueprint
import os
import sys
import uuid
import tempfile
import traceback
from werkzeug.utils import secure_filename

# Add ai_model to path for importing classifier
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
capstone_dir = os.path.dirname(backend_dir)
ai_model_path = os.path.join(capstone_dir, 'ai_model')

# Print debug info
print(f"Current dir: {current_dir}")
print(f"Backend dir: {backend_dir}")
print(f"Capstone dir: {capstone_dir}")
print(f"AI model path: {ai_model_path}")

if ai_model_path not in sys.path:
    sys.path.insert(0, ai_model_path)

# Import classifier from ai_model - Try both locations
try:
    # Try src/classifier first
    from src.classifier import HeartSoundClassifier
    print("✅ HeartSoundClassifier imported from src/classifier")
except ImportError as e:
    print(f"❌ Failed to import from src/classifier: {e}")
    try:
        # Try root classifier
        from classifier import HeartSoundClassifier
        print("✅ HeartSoundClassifier imported from root classifier")
    except ImportError as e2:
        print(f"❌ Failed to import from root classifier: {e2}")
        HeartSoundClassifier = None

# Create blueprint
heart_sound_bp = Blueprint('heart_sound', __name__, url_prefix='/api/v1/screening')

# Configuration
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'flac', 'm4a', 'aiff'}

# Find the model path
model_path = os.path.join(capstone_dir, 'ai_model', 'models', 'mitral_classifier_v4')

print(f"Looking for model at: {model_path}")
print(f"Model path exists: {os.path.exists(model_path)}")

if os.path.exists(model_path):
    # List files in model directory
    print(f"Files in model directory: {os.listdir(model_path)}")

# Initialize classifier
MODEL_PATH = model_path
classifier = None

try:
    if HeartSoundClassifier and os.path.exists(MODEL_PATH):
        # Check if model files exist
        model_file = os.path.join(MODEL_PATH, 'best_model.pkl')
        scaler_file = os.path.join(MODEL_PATH, 'scaler.pkl')
        
        if os.path.exists(model_file) and os.path.exists(scaler_file):
            classifier = HeartSoundClassifier(MODEL_PATH)
            print("✅ Classifier loaded successfully!")
        else:
            print(f"❌ Model files missing:")
            print(f"   best_model.pkl exists: {os.path.exists(model_file)}")
            print(f"   scaler.pkl exists: {os.path.exists(scaler_file)}")
            classifier = None
    else:
        print(f"❌ Could not load classifier:")
        print(f"   HeartSoundClassifier available: {HeartSoundClassifier is not None}")
        print(f"   MODEL_PATH: {MODEL_PATH}")
        print(f"   Path exists: {os.path.exists(MODEL_PATH)}")
        classifier = None
except Exception as e:
    print(f"❌ Failed to load classifier: {e}")
    traceback.print_exc()
    classifier = None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@heart_sound_bp.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': classifier is not None,
        'model_type': type(classifier.model).__name__ if classifier and hasattr(classifier, 'model') else None,
        'model_path': MODEL_PATH
    })

@heart_sound_bp.route('/info', methods=['GET'])
def info():
    """Get model information"""
    if classifier is None:
        return jsonify({'error': 'Classifier not loaded'}), 503
    
    info_data = {
        'model_type': type(classifier.model).__name__,
        'classes': classifier.classes,
        'sample_rate': classifier.sr,
        'supported_formats': list(ALLOWED_EXTENSIONS),
        'model_path': MODEL_PATH
    }
    
    if hasattr(classifier, 'feature_names') and classifier.feature_names:
        info_data['feature_count'] = len(classifier.feature_names)
    
    # Add feature importance if available
    if hasattr(classifier.model, 'feature_importances_'):
        importances = classifier.model.feature_importances_
        if hasattr(classifier, 'feature_names') and classifier.feature_names:
            top_features = sorted(
                zip(classifier.feature_names, importances),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            info_data['top_features'] = [
                {'name': name, 'importance': float(imp)} 
                for name, imp in top_features
            ]
    
    return jsonify(info_data)

@heart_sound_bp.route('/predict', methods=['POST'])
def predict():
    """Predict heart sound class from uploaded audio file"""
    try:
        # Check if classifier is loaded
        if classifier is None:
            return jsonify({'error': 'Classifier not loaded'}), 503
        
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'error': f'File type not allowed. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # Save uploaded file to temp location
        original_filename = secure_filename(file.filename)
        unique_id = str(uuid.uuid4())[:8]
        
        # Use temp directory
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            file.save(tmp_file.name)
            filepath = tmp_file.name
        
        try:
            # Predict
            result = classifier.predict(filepath, return_all=True)
            
            if result is None:
                return jsonify({'error': 'Failed to process audio file'}), 500
            
            # Generate visualization
            vis_base64 = classifier.generate_visualization(filepath)
            
            # Prepare response
            response = {
                'success': True,
                'filename': original_filename,
                'prediction': result['class'],
                'confidence': result['confidence'],
                'probabilities': {
                    'Normal': result['prob_normal'],
                    'RHD': result['prob_rhd']
                },
                'visualization': vis_base64,
                'top_features': result.get('top_features', []),
                'result_id': unique_id
            }
            
            return jsonify(response)
            
        finally:
            # Clean up temp file
            if os.path.exists(filepath):
                os.unlink(filepath)
    
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@heart_sound_bp.route('/batch_predict', methods=['POST'])
def batch_predict():
    """Predict multiple heart sound files"""
    try:
        if classifier is None:
            return jsonify({'error': 'Classifier not loaded'}), 503
        
        if 'files' not in request.files:
            return jsonify({'error': 'No files uploaded'}), 400
        
        files = request.files.getlist('files')
        
        if len(files) == 0:
            return jsonify({'error': 'No files selected'}), 400
        
        results = []
        errors = []
        
        for file in files:
            if file.filename == '':
                continue
            
            if not allowed_file(file.filename):
                errors.append({
                    'filename': file.filename,
                    'error': 'File type not allowed'
                })
                continue
            
            original_filename = secure_filename(file.filename)
            
            # Use temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                file.save(tmp_file.name)
                filepath = tmp_file.name
            
            try:
                result = classifier.predict(filepath, return_all=True)
                
                if result:
                    results.append({
                        'filename': original_filename,
                        'prediction': result['class'],
                        'confidence': result['confidence'],
                        'probabilities': {
                            'Normal': result['prob_normal'],
                            'RHD': result['prob_rhd']
                        }
                    })
                else:
                    errors.append({
                        'filename': original_filename,
                        'error': 'Failed to process audio'
                    })
            except Exception as e:
                errors.append({
                    'filename': original_filename,
                    'error': str(e)
                })
            finally:
                if os.path.exists(filepath):
                    os.unlink(filepath)
        
        return jsonify({
            'success': True,
            'total': len(results) + len(errors),
            'processed': len(results),
            'errors': len(errors),
            'results': results,
            'error_details': errors if errors else None
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500