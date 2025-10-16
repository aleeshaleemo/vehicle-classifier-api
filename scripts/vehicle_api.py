from flask import Flask, request, jsonify
from ultralytics import YOLO
import cv2
import numpy as np
from PIL import Image
import io
import base64
from datetime import datetime

app = Flask(__name__)

# Load your YOLOv8 model
MODEL_PATH = 'best.pt'  # Update with your model path
model = YOLO(MODEL_PATH)

# Class mapping (update based on your model's classes)
CLASS_NAMES = {
    0: 'front',
    1: 'rear'
}

def process_image(image_file):
    """Process uploaded image file"""
    try:
        # Read image
        image_bytes = image_file.read()
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return None, "Invalid image format"
        
        return img, None
    except Exception as e:
        return None, str(e)

def predict_vehicle_class(img):
    """Run YOLOv8 prediction on image"""
    try:
        # Run inference
        results = model(img, conf=0.25)
        
        predictions = []
        
        for result in results:
            boxes = result.boxes
            
            for box in boxes:
                # Get class ID and confidence
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                
                # Get bounding box coordinates
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                
                # Get class name
                class_name = CLASS_NAMES.get(cls_id, f"class_{cls_id}")
                
                predictions.append({
                    'class': class_name,
                    'confidence': round(conf, 4),
                    'bbox': {
                        'x1': round(x1, 2),
                        'y1': round(y1, 2),
                        'x2': round(x2, 2),
                        'y2': round(y2, 2)
                    }
                })
        
        return predictions, None
    except Exception as e:
        return None, str(e)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': model is not None,
        'timestamp': datetime.utcnow().isoformat()
    }), 200

@app.route('/predict', methods=['POST'])
def predict():
    """Main prediction endpoint"""
    try:
        # Check if image is in request
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No image file provided'
            }), 400
        
        image_file = request.files['image']
        
        # Check if file is empty
        if image_file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Empty filename'
            }), 400
        
        # Process image
        img, error = process_image(image_file)
        if error:
            return jsonify({
                'success': False,
                'error': error
            }), 400
        
        # Get predictions
        predictions, error = predict_vehicle_class(img)
        if error:
            return jsonify({
                'success': False,
                'error': error
            }), 500
        
        # Prepare response
        response = {
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'predictions': predictions,
            'count': len(predictions)
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/predict/base64', methods=['POST'])
def predict_base64():
    """Prediction endpoint for base64 encoded images"""
    try:
        data = request.get_json()
        
        if 'image' not in data:
            return jsonify({
                'success': False,
                'error': 'No image data provided'
            }), 400
        
        # Decode base64 image
        try:
            image_data = base64.b64decode(data['image'])
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return jsonify({
                    'success': False,
                    'error': 'Invalid image format'
                }), 400
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Failed to decode image: {str(e)}'
            }), 400
        
        # Get predictions
        predictions, error = predict_vehicle_class(img)
        if error:
            return jsonify({
                'success': False,
                'error': error
            }), 500
        
        # Prepare response
        response = {
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'predictions': predictions,
            'count': len(predictions)
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)