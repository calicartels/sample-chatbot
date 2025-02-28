# api/routes.py
"""
API routes for the ProAxion sensor installation chatbot.
"""
import os
import glob
import json
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Body, Query, Path
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Add parent directory to system path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.bot import InstallationBot
from config import STRUCTURED_DIR, IMAGES_DIR
from utils.storage import StorageManager

# Create router
router = APIRouter()

# Create storage manager
storage_manager = StorageManager()

# Chatbot instances cache (user_id -> bot)
chatbot_instances = {}

# Models
class ChatRequest(BaseModel):
    """Chat request model."""
    user_id: str
    message: str
    knowledge_base_id: Optional[str] = None

class ChatResponse(BaseModel):
    """Chat response model."""
    response: str
    media_files: Optional[List[Dict[str, str]]] = None
    current_step: Optional[int] = None
    total_steps: Optional[int] = None
    step_title: Optional[str] = None
    stage: Optional[str] = None

class KnowledgeBaseInfo(BaseModel):
    """Knowledge base information model."""
    id: str
    title: str
    created_at: str

class ListKnowledgeBasesResponse(BaseModel):
    """Response model for listing knowledge bases."""
    knowledge_bases: List[KnowledgeBaseInfo]

# Helper functions
def get_chatbot(user_id: str, kb_id: Optional[str] = None) -> InstallationBot:
    """Get or create a chatbot instance for the user."""
    if user_id not in chatbot_instances:
        # Find the knowledge base file
        if kb_id:
            kb_path = os.path.join(STRUCTURED_DIR, f"{kb_id}.json")
            if not os.path.exists(kb_path):
                raise HTTPException(status_code=404, detail=f"Knowledge base with ID {kb_id} not found")
        else:
            # Use the latest knowledge base if none specified
            kb_files = glob.glob(os.path.join(STRUCTURED_DIR, "kb_*.json"))
            if not kb_files:
                raise HTTPException(status_code=404, detail="No knowledge bases found")
            kb_path = max(kb_files, key=os.path.getmtime)
            kb_id = os.path.basename(kb_path).replace(".json", "")
        
        # Create chatbot instance
        chatbot_instances[user_id] = InstallationBot(kb_path)
    
    return chatbot_instances[user_id]

def extract_media_from_response(response: str) -> (str, List[Dict[str, str]]):
    """Extract media references from response and convert them to proper URLs."""
    media_files = []
    clean_response = response
    
    # Extract video references
    video_matches = []
    
    # Look for [VIDEO: path/to/video.mp4] pattern
    import re
    video_pattern = r'\[VIDEO: ([^\]]+)\]'
    
    for match in re.finditer(video_pattern, response):
        video_path = match.group(1)
        video_filename = os.path.basename(video_path)
        video_url = f"/videos/{video_filename}"
        
        # Add to media files list
        media_files.append({
            "type": "video",
            "url": video_url,
            "filename": video_filename,
            "original_path": video_path
        })
        
        # Store match information for replacement
        video_matches.append((match.group(0), video_url))
    
    # Replace video references with URLs
    for original, video_url in video_matches:
        clean_response = clean_response.replace(original, f"[VIDEO: {video_url}]")
    
    # Extract image references
    image_matches = []
    
    # Look for [IMAGE: path/to/image.jpg] pattern
    image_pattern = r'\[IMAGE: ([^\]]+)\]'
    
    for match in re.finditer(image_pattern, response):
        image_path = match.group(1)
        image_filename = os.path.basename(image_path)
        image_url = f"/images/{image_filename}"
        
        # Add to media files list
        media_files.append({
            "type": "image",
            "url": image_url,
            "filename": image_filename,
            "original_path": image_path
        })
        
        # Store match information for replacement
        image_matches.append((match.group(0), image_url))
    
    # Replace image references with URLs
    for original, image_url in image_matches:
        clean_response = clean_response.replace(original, f"[IMAGE: {image_url}]")
    
    # Also look for image references in markdown format: ![alt](path/to/image.jpg)
    markdown_image_pattern = r'!\[(.*?)\]\(([^)]+)\)'
    
    for match in re.finditer(markdown_image_pattern, response):
        alt_text = match.group(1)
        image_path = match.group(2)
        
        # Skip if it's already a URL
        if image_path.startswith("http"):
            continue
            
        image_filename = os.path.basename(image_path)
        image_url = f"/images/{image_filename}"
        
        # Add to media files list
        media_files.append({
            "type": "image",
            "url": image_url,
            "filename": image_filename,
            "original_path": image_path,
            "alt_text": alt_text
        })
        
        # Store match information for replacement
        image_matches.append((match.group(0), f"![{alt_text}]({image_url})"))
    
    # Replace markdown image references with URLs
    for original, image_url_md in image_matches:
        clean_response = clean_response.replace(original, image_url_md)
    
    return clean_response, media_files

def get_current_state_info(user_id: str) -> Dict:
    """Get current state information for the user."""
    bot = chatbot_instances.get(user_id)
    if not bot:
        return {}
    
    state = bot.state_manager.get_state(user_id)
    return {
        "stage": state.stage.name if state.stage else None,
        "current_step": state.current_step,
        "total_steps": bot._get_total_steps(state.installation_method) if state.installation_method else None,
        "machine_type": state.machine_type,
        "configuration": state.configuration
    }

# Routes
@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message to the chatbot and get a response."""
    try:
        # Get or create chatbot instance
        bot = get_chatbot(request.user_id, request.knowledge_base_id)
        
        # Process message
        response = bot.process_message(request.user_id, request.message)
        
        # Extract media references
        clean_response, media_files = extract_media_from_response(response)
        
        # Get current state information
        state_info = get_current_state_info(request.user_id)
        
        return ChatResponse(
            response=clean_response,
            media_files=media_files,
            current_step=state_info.get("current_step"),
            total_steps=state_info.get("total_steps"),
            step_title=f"Step {state_info.get('current_step')}" if state_info.get("current_step") else None,
            stage=state_info.get("stage")
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

@router.get("/knowledge-bases", response_model=ListKnowledgeBasesResponse)
async def list_knowledge_bases():
    """List available knowledge bases."""
    try:
        # Get list of knowledge bases
        docs = storage_manager.list_all_documents()
        
        # Filter for knowledge bases only
        kb_docs = [doc for doc in docs if doc["id"].startswith("kb_")]
        
        return ListKnowledgeBasesResponse(
            knowledge_bases=[
                KnowledgeBaseInfo(
                    id=doc["id"],
                    title=doc["title"],
                    created_at=doc["created_at"]
                )
                for doc in kb_docs
            ]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing knowledge bases: {str(e)}")

@router.get("/reset/{user_id}")
async def reset_chat(user_id: str):
    """Reset the chat for a user."""
    try:
        # Check if the user has a chatbot instance
        if user_id in chatbot_instances:
            # Reset the state
            chatbot_instances[user_id].state_manager.reset_state(user_id)
            # Send welcome message
            response = chatbot_instances[user_id].process_message(user_id, "reset")
            return {"status": "ok", "message": "Chat reset successfully", "welcome_message": response}
        else:
            return {"status": "ok", "message": "No active chat found for this user"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting chat: {str(e)}")

@router.get("/video/{filename}")
async def get_video(filename: str):
    """Get a video file."""
    video_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "videos", filename)
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail=f"Video file {filename} not found")
    
    return FileResponse(video_path, media_type="video/mp4")

@router.get("/image/{filename}")
async def get_image(filename: str):
    """Get an image file."""
    image_path = os.path.join(IMAGES_DIR, filename)
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail=f"Image file {filename} not found")
    
    return FileResponse(image_path)