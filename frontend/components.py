# frontend/components.py
"""
UI components for the Streamlit frontend.
"""
import re
import streamlit as st
from typing import Dict, List, Optional, Any

def display_welcome_header():
    """Display the welcome header with logo and title."""
    # Header with title and logo
    col1, col2 = st.columns([1, 5])
    
    with col1:
        # Logo placeholder (replace with actual logo if available)
        st.image("https://placehold.co/80x80/2978A0/white?text=P", width=80)
    
    with col2:
        st.title("ProAxion Sensor Installation Assistant")
        st.write("I'll help you determine optimal sensor placement and guide you through installation.")

def display_chat_message(content: str, is_user: bool):
    """Display a chat message with appropriate styling."""
    # Determine alignment and styling based on user or bot
    if is_user:
        # User message - right aligned
        col1, col2 = st.columns([1, 4])
        with col2:
            st.markdown(
                f"""
                <div style="background-color: #E8F0F7; padding: 10px; 
                border-radius: 10px; margin-bottom: 10px; text-align: right;">
                <b>You</b><br>{content}
                </div>
                """, 
                unsafe_allow_html=True
            )
    else:
        # Bot message - left aligned
        col1, col2 = st.columns([4, 1])
        with col1:
            # Process markdown in the content
            processed_content = process_message_content(content)
            
            st.markdown(
                f"""
                <div style="background-color: #F0F2F6; padding: 10px; 
                border-radius: 10px; margin-bottom: 10px;">
                <b>Assistant</b><br>{processed_content}
                </div>
                """, 
                unsafe_allow_html=True
            )

def process_message_content(content: str) -> str:
    """Process message content to handle special formatting and media references."""
    # Replace video references with placeholders
    content = re.sub(
        r'\[VIDEO: ([^\]]+)\]',
        r'<i>📹 Video reference: \1</i>',
        content
    )
    
    # Add basic markdown support
    # Note: Streamlit's markdown function already handles this, but for custom HTML we need to handle it ourselves
    
    # Convert bullet lists (* item)
    content = re.sub(
        r'^\s*\*\s+(.+)$',
        r'• \1<br>',
        content, 
        flags=re.MULTILINE
    )
    
    # Convert numbered lists (1. item)
    content = re.sub(
        r'^\s*(\d+)\.\s+(.+)$',
        r'\1. \2<br>',
        content,
        flags=re.MULTILINE
    )
    
    # Convert bold (**text**)
    content = re.sub(
        r'\*\*(.+?)\*\*',
        r'<b>\1</b>',
        content
    )
    
    # Convert italic (*text*)
    content = re.sub(
        r'\*(.+?)\*',
        r'<i>\1</i>',
        content
    )
    
    # Convert line breaks
    content = content.replace('\n\n', '<br><br>')
    content = content.replace('\n', '<br>')
    
    return content

def display_video_player(video_url: str):
    """Display a video player for the specified video URL."""
    # Video player title
    st.subheader("Installation Video")
    
    # Video player
    video_html = f"""
    <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 8px;">
        <video style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border-radius: 8px;" controls>
            <source src="{video_url}" type="video/mp4">
            Your browser does not support the video tag.
        </video>
    </div>
    """
    st.markdown(video_html, unsafe_allow_html=True)
    
    # Add a direct link in case the embedded player has issues
    st.markdown(f"[Open video in new window]({video_url})")

def display_media_sidebar(media_history: List[Dict[str, Any]]):
    """Display a sidebar with previously shown media files."""
    with st.expander("Media History", expanded=False):
        for i, media in enumerate(media_history):
            if media["type"] == "video":
                st.markdown(f"**Video {i+1}**: {media.get('filename', 'Unnamed')}")
                
                # Thumbnail and play button (simplified)
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"📹 {media.get('filename', 'Installation Video')}")
                
                with col2:
                    if st.button(f"Play", key=f"play_{i}"):
                        st.session_state.current_video = media["url"]
                        st.experimental_rerun()
            
            elif media["type"] == "image":
                st.markdown(f"**Image {i+1}**: {media.get('filename', 'Unnamed')}")
                st.image(media["url"], width=200)