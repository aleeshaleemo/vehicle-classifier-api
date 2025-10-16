#!/bin/bash

# Vehicle Classification API - Complete Installation Script
# Run this on Ubuntu/Debian server

echo "=========================================="
echo "Vehicle Classification API Installation"
echo "=========================================="

# 1. Update system packages
echo "Step 1: Updating system packages..."
sudo apt update
sudo apt upgrade -y

# 2. Install system dependencies
echo "Step 2: Installing system dependencies..."
sudo apt install -y python3 python3-pip python3-venv nginx git curl

# Optional: Install system libraries for OpenCV
sudo apt install -y libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev

# 3. Create project directory
echo "Step 3: Creating project directory..."
cd ~
mkdir -p vehicle-api
cd vehicle-api

# 4. Create and activate virtual environment
echo "Step 4: Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 5. Upgrade pip
echo "Step 5: Upgrading pip..."
pip install --upgrade pip

# 6. Install Python packages
echo "Step 6: Installing Python dependencies..."
pip install flask==3.0.0
pip install ultralytics==8.1.0
pip install opencv-python==4.8.1.78
pip install numpy==1.24.3
pip install pillow==10.1.0
pip install gunicorn==21.2.0

# Alternative: Install from requirements.txt
# pip install -r requirements.txt

# 7. Create app.py file
echo "Step 7: Creating app.py..."
cat > app.py << 'EOF'
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
EOF

# 8. Create requirements.txt
echo "Step 8: Creating requirements.txt..."
cat > requirements.txt << 'EOF'
flask==3.0.0
ultralytics==8.1.0
opencv-python==4.8.1.78
numpy==1.24.3
pillow==10.1.0
gunicorn==21.2.0
EOF

# 9. Set up systemd service
echo "Step 9: Setting up systemd service..."
PROJECT_DIR=$(pwd)
VENV_PATH="$PROJECT_DIR/venv"

sudo tee /etc/systemd/system/vehicle-api.service > /dev/null << EOF
[Unit]
Description=Vehicle Classification API
After=network.target

[Service]
User=$USER
Group=$USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$VENV_PATH/bin"
ExecStart=$VENV_PATH/bin/gunicorn --workers 4 --bind 127.0.0.1:5000 --timeout 300 app:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 10. Configure Nginx
echo "Step 10: Configuring Nginx..."
sudo tee /etc/nginx/sites-available/vehicle-api > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;  # Replace with your domain or IP
    
    client_max_body_size 20M;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
    
    location /health {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        access_log off;
    }
}
EOF

# Enable Nginx site
sudo ln -sf /etc/nginx/sites-available/vehicle-api /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# 11. Configure firewall (if UFW is installed)
echo "Step 11: Configuring firewall..."
if command -v ufw &> /dev/null; then
    sudo ufw allow 'Nginx Full'
    sudo ufw allow OpenSSH
    # sudo ufw enable  # Uncomment if you want to enable firewall
fi

# 12. Reload systemd and enable service
echo "Step 12: Enabling services..."
sudo systemctl daemon-reload
sudo systemctl enable vehicle-api
sudo systemctl restart nginx

echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "IMPORTANT: Next Steps"
echo "1. Copy your YOLOv8 model file to: $PROJECT_DIR/best.pt"
echo "   Example: cp /path/to/your/model.pt $PROJECT_DIR/best.pt"
echo ""
echo "2. Update CLASS_NAMES in app.py if needed"
echo "   Example: nano $PROJECT_DIR/app.py"
echo ""
echo "3. Start the service:"
echo "   sudo systemctl start vehicle-api"
echo ""
echo "4. Check service status:"
echo "   sudo systemctl status vehicle-api"
echo ""
echo "5. View logs:"
echo "   sudo journalctl -u vehicle-api -f"
echo ""
echo "6. Test the API:"
echo "   curl http://localhost/health"
echo "   curl -X POST -F 'image=@test.jpg' http://localhost/predict"
echo ""
echo "=========================================="