# frontend/app.py
"""
Streamlit frontend for the ProAxion sensor installation chatbot.
"""
import os
import sys
import uuid
import requests
import streamlit as st
from typing import Dict, List, Any

# Add parent directory to system path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import component functions
from frontend.components import (
    display_welcome_header,
    display_chat_message,
    display_video_player,
    display_media_sidebar
)

# API URL (configurable for development/production)
API_URL = os.environ.get("API_URL", "http://localhost:8000/api")

# Main app
def main():
    # Page config
    st.set_page_config(
        page_title="ProAxion Sensor Installation Assistant",
        page_icon="🔧",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize session state for chat history and user ID
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    if "user_id" not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())
    
    if "current_step" not in st.session_state:
        st.session_state.current_step = None
    
    if "total_steps" not in st.session_state:
        st.session_state.total_steps = None
    
    if "current_video" not in st.session_state:
        st.session_state.current_video = None
    
    if "media_history" not in st.session_state:
        st.session_state.media_history = []
    
    if "show_welcome" not in st.session_state:
        st.session_state.show_welcome = True
    
    # Display welcome header
    display_welcome_header()
    
    # Create main layout with columns
    col1, col2 = st.columns([2, 1])
    
    # Main chat area (left column)
    with col1:
        # Chat container with fixed height and scrolling
        chat_container = st.container()
        with chat_container:
            # Display chat history
            for message in st.session_state.chat_history:
                display_chat_message(
                    message["content"],
                    message["is_user"]
                )
        
        # User input area at the bottom of the chat
        st.write("---")
        
        # Step progress information if available
        if st.session_state.current_step and st.session_state.total_steps:
            step_progress = st.progress(st.session_state.current_step / st.session_state.total_steps)
            st.write(f"Step {st.session_state.current_step} of {st.session_state.total_steps}")
        
        # Next step button (only show in installation steps stage)
        # We'll determine this based on messages containing "Step X of Y"
        is_in_steps = any("Step " in msg["content"] and " of " in msg["content"] 
                           for msg in st.session_state.chat_history if not msg["is_user"])
        
        # Input and buttons in columns for better layout
        input_col, button_col = st.columns([3, 1])
        
        with input_col:
            user_input = st.text_input("Type your message:", key="user_message")
        
        with button_col:
            # Submit button for user input
            submit_button = st.button("Send")
            
            # Next step button (only shown during installation steps)
            if is_in_steps:
                next_step_button = st.button("Next Step")
            else:
                next_step_button = False
        
        # Handle submit button click or Enter key
        if submit_button and user_input:
            # Add user message to chat history
            st.session_state.chat_history.append({
                "content": user_input,
                "is_user": True
            })
            
            # Get response from API
            try:
                response = requests.post(
                    f"{API_URL}/chat",
                    json={
                        "user_id": st.session_state.user_id,
                        "message": user_input
                    }
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    bot_message = response_data["response"]
                    media_files = response_data.get("media_files", [])
                    
                    # Update session state with step information
                    st.session_state.current_step = response_data.get("current_step")
                    st.session_state.total_steps = response_data.get("total_steps")
                    
                    # Add bot message to chat history
                    st.session_state.chat_history.append({
                        "content": bot_message,
                        "is_user": False,
                        "media_files": media_files
                    })
                    
                    # Process media files
                    for media in media_files:
                        if media["type"] == "video":
                            st.session_state.current_video = media["url"]
                            # Add to media history
                            if media not in st.session_state.media_history:
                                st.session_state.media_history.append(media)
                else:
                    st.error(f"Error: {response.status_code} - {response.text}")
            except Exception as e:
                st.error(f"Error: {str(e)}")
            
            # Clear input
            st.session_state.user_message = ""
            
            # Force page refresh to show the update
            st.experimental_rerun()
        
        # Handle "Next Step" button
        if next_step_button:
            # Simulate user typing "next" or "continue"
            next_message = "next"
            
            # Add user message to chat history
            st.session_state.chat_history.append({
                "content": "→ [Next Step]",
                "is_user": True
            })
            
            # Get response from API
            try:
                response = requests.post(
                    f"{API_URL}/chat",
                    json={
                        "user_id": st.session_state.user_id,
                        "message": next_message
                    }
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    bot_message = response_data["response"]
                    media_files = response_data.get("media_files", [])
                    
                    # Update session state with step information
                    st.session_state.current_step = response_data.get("current_step")
                    st.session_state.total_steps = response_data.get("total_steps")
                    
                    # Add bot message to chat history
                    st.session_state.chat_history.append({
                        "content": bot_message,
                        "is_user": False,
                        "media_files": media_files
                    })
                    
                    # Process media files
                    for media in media_files:
                        if media["type"] == "video":
                            st.session_state.current_video = media["url"]
                            # Add to media history
                            if media not in st.session_state.media_history:
                                st.session_state.media_history.append(media)
                else:
                    st.error(f"Error: {response.status_code} - {response.text}")
            except Exception as e:
                st.error(f"Error: {str(e)}")
            
            # Force page refresh to show the update
            st.experimental_rerun()
    
    # Video and media sidebar (right column)
    with col2:
        # Video player for the current video
        if st.session_state.current_video:
            display_video_player(st.session_state.current_video)
        else:
            st.info("Video will appear here when available during installation steps.")
        
        # Media history in expandable section
        if st.session_state.media_history:
            display_media_sidebar(st.session_state.media_history)
    
    # Footer with reset button
    st.write("---")
    footer_col1, footer_col2 = st.columns([4, 1])
    
    with footer_col2:
        # Reset button
        if st.button("Reset Chat"):
            # Call reset API
            try:
                response = requests.get(f"{API_URL}/reset/{st.session_state.user_id}")
                if response.status_code == 200:
                    # Clear chat history
                    st.session_state.chat_history = []
                    st.session_state.media_history = []
                    st.session_state.current_video = None
                    st.session_state.current_step = None
                    st.session_state.total_steps = None
                    
                    # Add welcome message
                    welcome_message = response.json().get("welcome_message", "Chat reset successfully.")
                    st.session_state.chat_history.append({
                        "content": welcome_message,
                        "is_user": False
                    })
                    
                    st.success("Chat reset successfully!")
                    st.experimental_rerun()
                else:
                    st.error(f"Error resetting chat: {response.text}")
            except Exception as e:
                st.error(f"Error resetting chat: {str(e)}")
    
    # Start a new chat if history is empty
    if not st.session_state.chat_history and st.session_state.show_welcome:
        # Add welcome message through API
        try:
            response = requests.post(
                f"{API_URL}/chat",
                json={
                    "user_id": st.session_state.user_id,
                    "message": "hello"
                }
            )
            
            if response.status_code == 200:
                welcome_message = response.json()["response"]
                st.session_state.chat_history.append({
                    "content": welcome_message,
                    "is_user": False
                })
                st.session_state.show_welcome = False
                st.experimental_rerun()
        except Exception as e:
            st.error(f"Error starting chat: {str(e)}")

if __name__ == "__main__":
    main()