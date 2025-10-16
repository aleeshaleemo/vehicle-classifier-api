from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from datetime import datetime
import uvicorn
import os

app = FastAPI(title="Vehicle Classification API", docs_url=None, redoc_url=None, openapi_url=None)

@app.post("/predict")
async def predict_vehicle(file: UploadFile = File(...)):
    # Save uploaded file
    os.makedirs("uploads", exist_ok=True)
    filepath = os.path.join("uploads", file.filename)
    with open(filepath, "wb") as f:
        f.write(await file.read())

    # Example logic: replace this with your ML model inference
    result = {
        "success": True,
        "predicted_class": "rear",
        "confidence": 72.82,
        "probabilities": {"front": 27.18, "rear": 72.82},
        "filename": file.filename,
        "timestamp": datetime.now().isoformat()
    }

    return JSONResponse(content=result)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
