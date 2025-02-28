# api/main.py
"""
FastAPI backend for the ProAxion sensor installation chatbot.
Serves the chatbot API and static files.
"""
import os
import sys
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional

# Add parent directory to system path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from local modules
from api.routes import router
from config import IMAGES_DIR, STRUCTURED_DIR

# Get absolute path to videos directory
BASE_DIR = Path(__file__).resolve().parent.parent
VIDEOS_DIR = os.path.join(BASE_DIR, "data", "videos")

# Create FastAPI app
app = FastAPI(
    title="ProAxion Sensor Installation API",
    description="API for sensor installation chatbot",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins in development
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Mount static files
app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")
app.mount("/videos", StaticFiles(directory=VIDEOS_DIR), name="videos")

# Include API routes
app.include_router(router, prefix="/api")

# Error handling
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": f"Internal server error: {str(exc)}"},
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Root endpoint with API information
@app.get("/")
async def root():
    return {
        "name": "ProAxion Sensor Installation API",
        "version": "1.0.0",
        "endpoints": {
            "/api/chat": "Send messages to the chatbot",
            "/api/knowledge-bases": "Get available knowledge bases",
            "/videos/{filename}": "Access video files",
            "/images/{filename}": "Access image files",
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)