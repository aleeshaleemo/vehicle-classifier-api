from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import onnxruntime as ort
import numpy as np
from PIL import Image
import io
import os
from datetime import datetime
from pathlib import Path
import traceback

app = FastAPI(
    title="Vehicle Classification API",
    description="API for classifying vehicle images as front or rear view",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
CONFIG = {
    "model_path": os.getenv("MODEL_PATH", "models/best.onnx"),
    "corrections_dir": "corrections",
    "retrain_threshold": 50,
    "img_size": 224,
    "class_names": ["front", "rear"],
    "models_dir": "models",
    "dataset_dir": "dataset",
}

# Create necessary directories
for d in [
    "corrections/front", "corrections/rear",
    "dataset/train/front", "dataset/train/rear",
    "dataset/val/front", "dataset/val/rear", "models"
]:
    Path(d).mkdir(parents=True, exist_ok=True)

ort_session = None


def load_model():
    """Load ONNX model"""
    global ort_session
    try:
        if not os.path.exists(CONFIG["model_path"]):
            print(f"⚠ Model not found at {CONFIG['model_path']}")
            return False
        ort_session = ort.InferenceSession(
            CONFIG["model_path"],
            providers=['CPUExecutionProvider']
        )
        print("✅ Model loaded successfully!")
        return True
    except Exception as e:
        print("❌ Error loading model:", e)
        traceback.print_exc()
        return False


def preprocess_image(image: Image.Image):
    """Prepare image for ONNX model"""
    img = image.resize((CONFIG["img_size"], CONFIG["img_size"]))
    if img.mode != 'RGB':
        img = img.convert('RGB')
    arr = np.array(img).astype(np.float32) / 255.0
    arr = np.transpose(arr, (2, 0, 1))
    arr = np.expand_dims(arr, axis=0)
    return arr


def predict_image(image: Image.Image):
    """Run ONNX model prediction"""
    if ort_session is None:
        raise HTTPException(status_code=500, detail="Model not loaded")

    try:
        input_tensor = preprocess_image(image)
        input_name = ort_session.get_inputs()[0].name
        outputs = ort_session.run(None, {input_name: input_tensor})
        logits = outputs[0][0]
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / exp_logits.sum()
        pred_idx = int(np.argmax(probs))
        
        return {
            "predicted_class": CONFIG["class_names"][pred_idx],
            "confidence": round(float(probs[pred_idx]) * 100, 2),
            "probabilities": {
                CONFIG["class_names"][i]: round(float(probs[i]) * 100, 2)
                for i in range(len(CONFIG["class_names"]))
            }
        }
    except Exception as e:
        print("❌ Prediction failed:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@app.on_event("startup")
async def startup_event():
    """Initialize model on startup"""
    print("\n🚗 Starting Vehicle Classification API")
    if load_model():
        print("✅ API ready for requests\n")
    else:
        print("⚠️ API started but model not loaded\n")


@app.get("/")
async def root():
    """API root endpoint - basic info"""
    return {
        "service": "Vehicle Classification API",
        "version": "1.0.0",
        "status": "running",
        "model_loaded": ort_session is not None,
        "endpoints": {
            "predict": "/predict - POST image file to get classification",
            "correct": "/correct - POST to submit correction",
            "stats": "/stats - GET current statistics",
            "health": "/health - GET health check"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy" if ort_session is not None else "degraded",
        "model_loaded": ort_session is not None,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    """
    Predict vehicle orientation from image
    
    Returns JSON:
    {
        "success": true,
        "predicted_class": "front",
        "confidence": 95.67,
        "probabilities": {
            "front": 95.67,
            "rear": 4.33
        },
        "filename": "image.jpg",
        "timestamp": "2025-10-14T10:30:00"
    }
    """
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400, 
                detail="Invalid file type. Only images are accepted."
            )
        
        # Read and process image
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        
        # Get prediction
        result = predict_image(image)
        
        # Add metadata
        result["success"] = True
        result["filename"] = file.filename
        result["timestamp"] = datetime.now().isoformat()
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        print("❌ Error during prediction:\n", traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "message": "Prediction failed"
            }
        )


@app.post("/correct")
async def correct_prediction(
    file: UploadFile = File(...),
    predicted_class: str = Form(...),
    correct_class: str = Form(...)
):
    """
    Submit correction for wrong prediction
    
    Returns JSON with correction status and retraining info
    """
    try:
        # Validate correct class
        if correct_class not in CONFIG["class_names"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid class. Must be one of: {CONFIG['class_names']}"
            )
        
        # Read and save image
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        save_path = os.path.join(CONFIG["corrections_dir"], correct_class, filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        image.save(save_path)
        
        print(f"✅ Correction saved: {predicted_class} → {correct_class}")
        
        # Count total corrections
        corrections_front = len(os.listdir("corrections/front"))
        corrections_rear = len(os.listdir("corrections/rear"))
        total_corrections = corrections_front + corrections_rear
        
        # Check if retraining threshold reached
        retraining_triggered = total_corrections >= CONFIG["retrain_threshold"]
        
        response = {
            "success": True,
            "message": "Correction saved successfully",
            "correction_count": total_corrections,
            "threshold": CONFIG["retrain_threshold"],
            "retraining_triggered": retraining_triggered,
            "corrections_by_class": {
                "front": corrections_front,
                "rear": corrections_rear
            }
        }
        
        if retraining_triggered:
            response["message"] += " - Retraining will be triggered"
        
        return JSONResponse(content=response)
        
    except Exception as e:
        print("❌ Correction error:\n", traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "message": "Correction failed"
            }
        )


@app.get("/stats")
async def get_stats():
    """Get current API statistics"""
    corrections_front = len(os.listdir("corrections/front")) if os.path.exists("corrections/front") else 0
    corrections_rear = len(os.listdir("corrections/rear")) if os.path.exists("corrections/rear") else 0
    total_corrections = corrections_front + corrections_rear
    
    return JSONResponse(content={
        "success": True,
        "correction_count": total_corrections,
        "threshold": CONFIG["retrain_threshold"],
        "progress_percentage": round((total_corrections / CONFIG["retrain_threshold"]) * 100, 2),
        "corrections_by_class": {
            "front": corrections_front,
            "rear": corrections_rear
        },
        "model_loaded": ort_session is not None,
        "model_path": CONFIG["model_path"]
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)