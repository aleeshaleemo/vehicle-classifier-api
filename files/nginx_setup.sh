#!/bin/bash
# Complete setup script for Ubuntu/Debian server with Nginx

# ============================================
# 1. INSTALL DEPENDENCIES
# ============================================

echo "📦 Installing system dependencies..."
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3-pip nginx git

# ============================================
# 2. CREATE APPLICATION DIRECTORY
# ============================================

echo "📁 Creating application directory..."
sudo mkdir -p /var/www/vehicle-api
sudo chown -R $USER:$USER /var/www/vehicle-api
cd /var/www/vehicle-api

# ============================================
# 3. SETUP PYTHON VIRTUAL ENVIRONMENT
# ============================================

echo "🐍 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install fastapi uvicorn[standard] python-multipart onnxruntime numpy Pillow ultralytics

# ============================================
# 4. CREATE DIRECTORY STRUCTURE
# ============================================

echo "📂 Creating directory structure..."
mkdir -p corrections/front corrections/rear
mkdir -p dataset/train/front dataset/train/rear
mkdir -p dataset/val/front dataset/val/rear
mkdir -p models

# Copy your files here:
# - app.py (the updated version above)
# - models/best.onnx (your model file)

# ============================================
# 5. CREATE SYSTEMD SERVICE
# ============================================

echo "⚙️ Creating systemd service..."
sudo tee /etc/systemd/system/vehicle-api.service > /dev/null <<EOF
[Unit]
Description=Vehicle Classification API
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/var/www/vehicle-api
Environment="PATH=/var/www/vehicle-api/venv/bin"
ExecStart=/var/www/vehicle-api/venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# ============================================
# 6. CONFIGURE NGINX
# ============================================

echo "🌐 Configuring Nginx..."
sudo tee /etc/nginx/sites-available/vehicle-api > /dev/null <<'EOF'
server {
    listen 80;
    server_name _; # Replace with your domain or IP

    # Increase client body size for image uploads
    client_max_body_size 50M;

    # API endpoints
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Timeouts for long requests
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Health check endpoint (optional)
    location /health {
        access_log off;
        proxy_pass http://127.0.0.1:8000/health;
    }
}
EOF

# Enable the site
sudo ln -sf /etc/nginx/sites-available/vehicle-api /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
sudo nginx -t

# ============================================
# 7. CONFIGURE FIREWALL
# ============================================

echo "🔥 Configuring firewall..."
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS (for future SSL)
sudo ufw --force enable

# ============================================
# 8. START SERVICES
# ============================================

echo "🚀 Starting services..."
sudo systemctl daemon-reload
sudo systemctl enable vehicle-api
sudo systemctl start vehicle-api
sudo systemctl restart nginx

# ============================================
# 9. CHECK STATUS
# ============================================

echo ""
echo "✅ Installation complete!"
echo ""
echo "📊 Service Status:"
sudo systemctl status vehicle-api --no-pager
echo ""
echo "🌐 Nginx Status:"
sudo systemctl status nginx --no-pager
echo ""
echo "🔍 Check logs with:"
echo "   sudo journalctl -u vehicle-api -f"
echo ""
echo "📡 API should be accessible at: http://YOUR_SERVER_IP"
echo ""