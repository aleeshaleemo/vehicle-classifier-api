from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import onnxruntime as ort
from PIL import Image
import numpy as np
from io import BytesIO
import logging
from typing import Dict, List  # ✅ updated here
import os

from app.utils import preprocess_image, postprocess_output, get_class_name

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Vehicle Classification API",
    description="YOLOv8 ONNX-based vehicle front/rear classification API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_PATH = "app/model/classifier.onnx"
MODEL_INPUT_SIZE = (224, 224)
session = None


@app.on_event("startup")
async def load_model():
    global session
    try:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model file not found at {MODEL_PATH}")
        
        logger.info(f"Loading ONNX model from {MODEL_PATH}")
        session = ort.InferenceSession(
            MODEL_PATH,
            providers=["CPUExecutionProvider"]
        )
        
        input_name = session.get_inputs()[0].name
        input_shape = session.get_inputs()[0].shape
        output_name = session.get_outputs()[0].name
        
        logger.info(f"Model loaded successfully!")
        logger.info(f"Input: {input_name} - Shape: {input_shape}")
        logger.info(f"Output: {output_name}")
        
    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}")
        raise


@app.get("/")
async def root() -> Dict:
    return {
        "message": "Vehicle Classification API is running!",
        "version": "1.0.0",
        "status": "healthy",
        "model_loaded": session is not None
    }


@app.get("/health")
async def health_check() -> Dict:
    if session is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {"status": "healthy", "model": "loaded"}


@app.post("/predict")
async def predict(file: UploadFile = File(...)) -> JSONResponse:
    if session is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload an image file."
        )
    
    try:
        logger.info(f"Processing image: {file.filename}")
        contents = await file.read()
        image = Image.open(BytesIO(contents)).convert("RGB")
        
        input_data = preprocess_image(image, input_size=MODEL_INPUT_SIZE)
        
        input_name = session.get_inputs()[0].name
        output_name = session.get_outputs()[0].name
        
        logger.info("Running inference...")
        outputs = session.run([output_name], {input_name: input_data})
        
        pred_index, confidence = postprocess_output(outputs[0])
        label = get_class_name(pred_index)
        
        logger.info(f"Prediction: {label} (confidence: {confidence:.3f})")
        
        return JSONResponse({
            "success": True,
            "prediction": {
                "label": label,
                "class_index": pred_index,
                "confidence": round(confidence, 4)
            },
            "filename": file.filename
        })
        
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}"
        )


from typing import List  # Add this import at the top

@app.post("/batch_predict")
async def batch_predict(files: List[UploadFile] = File(...)) -> JSONResponse:
    if session is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    if len(files) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 images allowed per batch"
        )
    
    results = []
    
    for file in files:
        try:
            contents = await file.read()
            image = Image.open(BytesIO(contents)).convert("RGB")
            
            input_data = preprocess_image(image, input_size=MODEL_INPUT_SIZE)
            
            input_name = session.get_inputs()[0].name
            output_name = session.get_outputs()[0].name
            
            outputs = session.run([output_name], {input_name: input_data})
            pred_index, confidence = postprocess_output(outputs[0])
            label = get_class_name(pred_index)
            
            results.append({
                "filename": file.filename,
                "success": True,
                "prediction": {
                    "label": label,
                    "class_index": pred_index,
                    "confidence": round(confidence, 4)
                }
            })
            
        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e)
            })
    
    return JSONResponse({
        "success": True,
        "total_images": len(files),
        "results": results
    })
