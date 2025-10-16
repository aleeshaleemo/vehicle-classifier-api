# Vehicle Classification API - Quick Reference

## 🔗 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information |
| GET | `/health` | Health check |
| POST | `/predict` | Classify vehicle image |
| POST | `/correct` | Submit correction |
| GET | `/stats` | Get statistics |

---

## 📝 Usage Examples

### Using cURL

```bash
# Health check
curl http://YOUR_SERVER_IP/health

# Predict image
curl -X POST http://YOUR_SERVER_IP/predict \
  -F "file=@vehicle.jpg"

# Submit correction
curl -X POST http://YOUR_SERVER_IP/correct \
  -F "file=@vehicle.jpg" \
  -F "predicted_class=front" \
  -F "correct_class=rear"

# Get stats
curl http://YOUR_SERVER_IP/stats
```

### Using Python

```python
import requests

# Predict
with open('vehicle.jpg', 'rb') as f:
    response = requests.post(
        'http://YOUR_SERVER_IP/predict',
        files={'file': f}
    )
print(response.json())

# Correction
with open('vehicle.jpg', 'rb') as f:
    response = requests.post(
        'http://YOUR_SERVER_IP/correct',
        files={'file': f},
        data={
            'predicted_class': 'front',
            'correct_class': 'rear'
        }
    )
print(response.json())
```

### Using JavaScript/Fetch

```javascript
// Predict
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('http://YOUR_SERVER_IP/predict', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => console.log(data));
```

---

## 🛠️ Server Management

### Check Service Status
```bash
# Ubuntu/Linux
sudo systemctl status vehicle-api
sudo systemctl status nginx

# Windows
Get-Service VehicleAPI
Get-Service Nginx
```

### Restart Services
```bash
# Ubuntu/Linux
sudo systemctl restart vehicle-api
sudo systemctl restart nginx

# Windows
nssm restart VehicleAPI
nssm restart Nginx
```

### View Logs
```bash
# Ubuntu/Linux
sudo journalctl -u vehicle-api -f
sudo tail -f /var/log/nginx/access.log

# Windows
Get-Content C:\vehicle-api\app.log -Tail 50 -Wait
```

### Update API
```bash
# Upload new app.py
scp app.py ubuntu@SERVER:/var/www/vehicle-api/

# Restart
ssh ubuntu@SERVER
sudo systemctl restart vehicle-api
```

---

## 🔧 Nginx Configuration

### Ubuntu Location
```
/etc/nginx/sites-available/vehicle-api
```

### Windows Location
```
C:\nginx\conf\nginx.conf
```

### Test Configuration
```bash
# Ubuntu
sudo nginx -t

# Windows
C:\nginx\nginx.exe -t
```

### Reload Configuration
```bash
# Ubuntu
sudo systemctl reload nginx

# Windows
C:\nginx\nginx.exe -s reload
```

---

## 🐛 Troubleshooting

### API Not Responding

```bash
# Check if service is running
sudo systemctl status vehicle-api

# Check logs
sudo journalctl -u vehicle-api -n 50

# Test manually
cd /var/www/vehicle-api
source venv/bin/activate
python app.py
```

### Nginx 502 Bad Gateway

```bash
# Check if API is running
curl http://127.0.0.1:8000/health

# Check Nginx error log
sudo tail -f /var/log/nginx/error.log

# Restart both services
sudo systemctl restart vehicle-api nginx
```

### Port Already in Use

```bash
# Find process using port 8000
sudo lsof -i :8000
# or
sudo netstat -tulpn | grep 8000

# Kill the process
sudo kill -9 PID
```

### File Upload Too Large

```nginx
# Update nginx.conf
client_max_body_size 50M;

# Restart nginx
sudo systemctl restart nginx
```

---

## 📊 Monitoring

### Check System Resources
```bash
# CPU and Memory
top
htop

# Disk space
df -h

# API process info
ps aux | grep python
```

### Check Request Count
```bash
# Count requests in last hour
sudo grep "POST /predict" /var/log/nginx/access.log | wc -l
```

### Monitor in Real-Time
```bash
# Watch API logs
watch -n 1 'sudo journalctl -u vehicle-api -n 10'

# Watch Nginx access
tail -f /var/log/nginx/access.log | grep predict
```

---

## 🔐 Security

### Add Basic Authentication
```bash
# Install tools
sudo apt install apache2-utils

# Create password
sudo htpasswd -c /etc/nginx/.htpasswd apiuser

# Update nginx config
sudo nano /etc/nginx/sites-available/vehicle-api

# Add inside location block:
auth_basic "Restricted Access";
auth_basic_user_file /etc/nginx/.htpasswd;

# Restart
sudo systemctl restart nginx
```

### Enable HTTPS
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal
sudo certbot renew --dry-run
```

---

## 📦 Backup & Restore

### Backup Corrections
```bash
# Create backup
tar -czf corrections_backup_$(date +%Y%m%d).tar.gz corrections/

# Download backup
scp ubuntu@SERVER:/var/www/vehicle-api/corrections_backup*.tar.gz ./
```

### Backup Model
```bash
# Create backup
cp models/best.onnx models/best_backup_$(date +%Y%m%d).onnx
```

### Restore
```bash
# Extract corrections
tar -xzf corrections_backup_20251014.tar.gz

# Restore model
cp models/best_backup_20251014.onnx models/best.onnx

# Restart service
sudo systemctl restart vehicle-api
```

---

## 🚀 Performance Tuning

### Increase Workers
```python
# In systemd service file
ExecStart=/var/www/vehicle-api/venv/bin/uvicorn app:app \
  --host 127.0.0.1 --port 8000 --workers 4
```

### Enable Gzip in Nginx
```nginx
gzip on;
gzip_types application/json;
gzip_min_length 1000;
```

### Add Caching
```nginx
# Cache static responses
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m;

location /stats {
    proxy_cache api_cache;
    proxy_cache_valid 200 1m;
    proxy_pass http://127.0.0.1:8000;
}
```