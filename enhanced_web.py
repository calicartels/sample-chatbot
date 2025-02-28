#!/usr/bin/env python3
"""
Enhanced Streamlit web interface for the Sensor Installation Chatbot.
This version is tailored to work with your existing knowledge base structure.
"""
import os
import sys
import uuid
import re
import json
import streamlit as st
from google.cloud import storage
from google.oauth2.service_account import Credentials
from typing import Dict, List, Any, Optional

# Add parent directory to system path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Import chatbot
from rag.bot import InstallationBot
from config import STRUCTURED_DIR, IMAGES_DIR

class EnhancedChatInterface:
    """Enhanced chat interface with video and image support."""
    
    def __init__(self):
        """Initialize the chat interface."""
        # Set up page configuration
        st.set_page_config(
            page_title="ProAxion Sensor Installation Assistant",
            page_icon="🔧",
            layout="wide",
            initial_sidebar_state="collapsed"
        )
        
        # Ensure Google project ID is set
        os.environ["GOOGLE_CLOUD_PROJECT"] = "capstone-449418"
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(current_dir, "credentials", "capstone-449418-38bd0569f608.json")
        
        # Initialize state
        self._initialize_state()
        
        # Initialize GCS client and bot
        self._initialize_services()
        
        # Set up layout - creates UI elements and session state variables
        self._setup_layout()
        
    
    def _initialize_state(self):
        """Initialize session state variables."""
        # Chat state
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        if "user_id" not in st.session_state:
            st.session_state.user_id = str(uuid.uuid4())
        
        # Video state
        if "current_step" not in st.session_state:
            st.session_state.current_step = None
        
        if "current_segment" not in st.session_state:
            st.session_state.current_segment = None
        
        if "video_url" not in st.session_state:
            st.session_state.video_url = None
        
        # Images state
        if "concept_images" not in st.session_state:
            st.session_state.concept_images = {}
        
        if "current_concept" not in st.session_state:
            st.session_state.current_concept = None
        
        # Service state
        if "storage_client" not in st.session_state:
            st.session_state.storage_client = None
        
        if "bot" not in st.session_state:
            st.session_state.bot = None
        
        if "kb_data" not in st.session_state:
            st.session_state.kb_data = None
    
    def _initialize_services(self):
        """Initialize GCS client and chatbot."""
        if st.session_state.storage_client is None:
            # Look for service account key in credentials directory
            credentials_dir = os.path.join(current_dir, "credentials")
            service_account_keys = [
                f for f in os.listdir(credentials_dir) 
                if f.endswith('.json') and 'client_secret' not in f
            ]
            
            if service_account_keys:
                # Use the most recent key
                key_path = os.path.join(credentials_dir, max(service_account_keys, 
                                       key=lambda f: os.path.getmtime(os.path.join(credentials_dir, f))))
                
                st.sidebar.info(f"Using service account key: {os.path.basename(key_path)}")
                
                try:
                    credentials = Credentials.from_service_account_file(
                        key_path,
                        scopes=['https://www.googleapis.com/auth/cloud-platform']
                    )
                    st.session_state.storage_client = storage.Client(credentials=credentials)
                    st.sidebar.success(f"✅ Successfully initialized GCS client")
                except Exception as e:
                    st.sidebar.error(f"❌ Error initializing GCS client: {e}")
            else:
                st.sidebar.error("❌ No service account key found in credentials directory")
        
        if st.session_state.bot is None:
            # Get knowledge base path
            kb_path = self._get_kb_path()
            if not kb_path:
                st.error("No knowledge base files found.")
                st.stop()
            
            # Load knowledge base data
            try:
                with open(kb_path, 'r') as f:
                    st.session_state.kb_data = json.load(f)
                    st.sidebar.success(f"✅ Loaded knowledge base: {os.path.basename(kb_path)}")
            except Exception as e:
                st.error(f"Error loading knowledge base: {e}")
                st.stop()
            
            # Initialize bot
            st.session_state.bot = InstallationBot(kb_path, storage_client=st.session_state.storage_client)
            
            # Initialize video URL
            if st.session_state.storage_client:
                video_uri = self._get_video_uri_from_kb()
                if video_uri:
                    st.session_state.video_url = self._get_signed_url(video_uri)
                    st.sidebar.success(f"✅ Generated signed URL for video")
                else:
                    st.sidebar.warning("⚠️ No video URI found in knowledge base")
            
            # Load concept images
            self._load_concept_images()
            
            # Send welcome message
            if not st.session_state.messages:
                welcome_message = st.session_state.bot.process_message(st.session_state.user_id, "hello")
                st.session_state.messages.append({"role": "assistant", "content": welcome_message})
    
    def _get_kb_path(self):
        """Get the path to the latest knowledge base."""
        import glob
        kb_files = glob.glob(os.path.join(STRUCTURED_DIR, "kb_*.json"))
        if not kb_files:
            return None
        
        # Use the latest file
        return max(kb_files, key=os.path.getmtime)
    
    def _get_video_uri_from_kb(self):
        """Extract video URI from knowledge base."""
        kb_data = st.session_state.kb_data
        if not kb_data:
            return None
        
        # Look for video URI in installation methods
        for machine in kb_data.get("machines", []):
            for method in machine.get("installation_methods", []):
                if "videos" in method and method["videos"]:
                    for video in method["videos"]:
                        if "uri" in video:
                            return video["uri"]
        
        return None
    
    def _get_signed_url(self, gcs_uri, expiration=3600):
        """Generate a signed URL for a GCS object."""
        if not st.session_state.storage_client:
            return None
            
        try:
            # Parse the GCS URI
            from urllib.parse import urlparse
            parsed_url = urlparse(gcs_uri)
            if parsed_url.scheme != 'gs':
                return gcs_uri  # Not a GCS URI, return as is
            
            bucket_name = parsed_url.netloc
            blob_path = parsed_url.path.lstrip('/')
            
            # Create a signed URL
            bucket = st.session_state.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            
            url = blob.generate_signed_url(
                version="v4",
                expiration=expiration,
                method="GET"
            )
            
            return url
        
        except Exception as e:
            st.sidebar.error(f"Error generating signed URL: {e}")
            return None
    
    def _load_concept_images(self):
        """Load concept images from knowledge base."""
        kb_data = st.session_state.kb_data
        if not kb_data:
            return
        
        # Get image associations
        image_associations = kb_data.get("image_associations", {})
        
        if not image_associations:
            st.sidebar.warning("⚠️ No image associations found in knowledge base.")
            st.sidebar.info("Run knowledge_base_update.py to add concept-to-image associations.")
            return
        
        # Get list of available image files
        if os.path.exists(IMAGES_DIR):
            image_files = os.listdir(IMAGES_DIR)
            st.sidebar.success(f"Found {len(image_files)} images in directory")
        else:
            st.sidebar.error(f"Images directory not found: {IMAGES_DIR}")
            os.makedirs(IMAGES_DIR, exist_ok=True)
            image_files = []
        
        # For each concept, find all matching images
        for concept, filenames in image_associations.items():
            st.session_state.concept_images[concept] = []
            for image_name in filenames:
                # Check if any available image contains part of the filename
                matching_images = [f for f in image_files if f.endswith('.jpg') or f.endswith('.png')]
                for img in matching_images:
                    image_path = os.path.join(IMAGES_DIR, img)
                    st.session_state.concept_images[concept].append({
                        "filename": img,
                        "path": image_path,
                        "url": f"file://{image_path}"
                    })
        
        # Log success
        concepts_with_images = [c for c, imgs in st.session_state.concept_images.items() if imgs]
        if concepts_with_images:
            st.sidebar.success(f"✅ Found images for {len(concepts_with_images)} concepts")
        else:
            st.sidebar.warning("No images found for any concepts")
    
    def _get_concept_for_message(self, message, user_input=None):
        """Determine relevant concept for a message."""
        # First check user input if provided
        if user_input:
            user_message = user_input.lower()
            if "belt" in user_message:
                return "belt_driven_fan"
            elif "direct" in user_message or "close coupled" in user_message:
                return "direct_coupled_fan"
            elif "independent" in user_message or "bearing" in user_message:
                return "independent_bearing_fan"
            elif "center hung" in user_message or "center-hung" in user_message:
                return "center_hung_vs_overhung"
            elif "overhung" in user_message:
                return "center_hung_vs_overhung"
        
        # Original logic for bot messages
        message = message.lower()
        if "center hung or overhung" in message:
            return "center_hung_vs_overhung"
        
        if "belt driven" in message:
            return "belt_driven_fan"
        elif "direct" in message and "coupled" in message:
            return "direct_coupled_fan"
        elif "independent bearing" in message:
            return "independent_bearing_fan"
        
        # Check for installation method question
        if "installation method" in message or "proceed with this method" in message:
            return "installation_methods"
        
        # Check for specific installation methods
        if "drill and tap" in message or "drill" in message or "tap" in message:
            return "drill_and_tap"
        
        if "epoxy" in message or "adhesive" in message:
            return "epoxy_mount"
        
        # Check for specific step mentions
        if "thread locker" in message or "apply" in message and "silicone" in message or "tighten" in message and "sensor" in message:
            return "sensor_installation"
        
        return None
    
    def _setup_layout(self):
        """Set up the page layout."""
        # Header
        st.title("ProAxion Sensor Installation Assistant")
        st.markdown("---")
        
        # Create main columns - chat on left, media on right
        self.chat_col, self.media_col = st.columns([3, 2])
        
        # Set up media column (right side)
        with self.media_col:
            self._setup_media_display()
        
        # Set up chat column (left side)
        with self.chat_col:
            self._setup_chat_interface()
    
    def _setup_media_display(self):
        """Set up the media display area."""
        # Create tabs for video and images
        video_tab, images_tab = st.tabs(["Installation Video", "Reference Images"])
        
        # Video tab
        with video_tab:
            self._setup_video_player()
        
        # Images tab
        with images_tab:
            self._setup_image_display()
    
    def _setup_video_player(self):
        """Set up the video player."""
        st.subheader("Installation Video")
        
        # Update current step from chat history
        self._update_current_step()
        
        # Get video segments
        segments = self._get_video_segments()
        
        if not segments:
            st.info("Video segments will be available when you begin installation.")
            return
        
        # Create a dropdown to select video segments
        segment_options = {f"{s.get('title', f'Segment {i}')} ({s.get('start', '0:00')}-{s.get('end', '0:00')})": i 
                        for i, s in enumerate(segments)}
        
        # Default to current step segment if available
        default_idx = 0
        if st.session_state.current_step is not None:
            for i, segment in enumerate(segments):
                if segment.get("step_reference") == st.session_state.current_step:
                    default_idx = i
                    break
        
        selected_segment_idx = st.selectbox(
            "Jump to segment:",
            options=list(segment_options.keys()),
            index=default_idx
        )
        
        selected_segment = segments[segment_options[selected_segment_idx]]
        
        # Display title and description of current segment
        st.markdown(f"**{selected_segment.get('title', 'Video Segment')}**")
        st.markdown(selected_segment.get("description", ""))
        
        # Show progress bar for steps
        if st.session_state.current_step is not None:
            max_steps = max(6, max(s.get("step_reference", 0) for s in segments) + 1)
            current_step_normalized = min(st.session_state.current_step + 1, max_steps) / max_steps
            st.progress(current_step_normalized)
        
        # Display video with start time parameter
        if st.session_state.video_url:
            start_time = self._time_to_seconds(selected_segment.get("start", "0:00"))
            
            # Create HTML with start time parameter
            video_html = f"""
            <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%;">
                <video style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;" controls>
                    <source src="{st.session_state.video_url}#t={start_time}" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
            </div>
            """
            st.markdown(video_html, unsafe_allow_html=True)
            
            # Use cleaner text to indicate the video segment
            st.markdown(f"Video segment: {selected_segment.get('start', '0:00')}-{selected_segment.get('end', 'end')}")
        else:
            st.warning("Video not available. Please check your GCS configuration.")
    
    def _setup_image_display(self):
        """Set up the image display area."""
        st.subheader("Reference Images")
        
        # Determine which concept to show based on conversation
        if st.session_state.current_concept and st.session_state.current_concept in st.session_state.concept_images:
            concept = st.session_state.current_concept
            images = st.session_state.concept_images[concept]
            
            # Limit to only 2 most relevant images
            images = images[:2]
            
            if images:
                # Show concept explanation from knowledge base
                if st.session_state.kb_data and "concept_explanations" in st.session_state.kb_data:
                    concept_explanation = st.session_state.kb_data["concept_explanations"].get(concept, {})
                    if concept_explanation:
                        # Display concept explanation
                        concept_name = concept.replace('_', ' ').title()
                        st.markdown(f"**{concept_name}**")
                        for key, value in concept_explanation.items():
                            if key != "images":
                                st.markdown(f"**{key.replace('_', ' ').title()}**: {value}")
                
                # Display images in a grid with proper captions
                cols = st.columns(min(2, len(images)))
                for i, image in enumerate(images):
                    with cols[i % len(cols)]:
                        try:
                            # Generate better caption
                            caption = concept.replace('_', ' ').title()
                            if i == 0:
                                caption += " - Diagram"
                            elif i == 1:
                                caption += " - Example"
                            
                            # For GCS images with signed URLs
                            if image["url"].startswith("http"):
                                st.image(image["url"], caption=caption, use_container_width=True)
                            # For local files
                            elif os.path.exists(image["path"]):
                                from PIL import Image as PILImage
                                img = PILImage.open(image["path"])
                                st.image(img, caption=caption, use_container_width=True)
                            else:
                                st.error(f"Image not found: {image['filename']}")
                        except Exception as e:
                            st.error(f"Error displaying image: {e}")
            else:
                st.info("No reference images available for the current topic.")
        else:
            # Show image selection
            st.info("Select a configuration to see reference images.")
    
    def _setup_chat_interface(self):
        """Set up the chat interface."""
        # Display chat messages
        message_container = st.container(height=400)
        with message_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.write(message["content"])
        
        # Chat input and controls
        st.markdown("---")
        
        # Step progress information if available
        if st.session_state.current_step is not None:
            st.write(f"**Current step: {st.session_state.current_step+1}/6**")
        
        # Create a form to prevent automatic reruns
        with st.form(key="chat_form", clear_on_submit=True):
            # Input row
            input_col, button_col1, button_col2 = st.columns([3, 1, 1])
            
            with input_col:
                user_input = st.text_input("Type your message here:", key="form_input")
            
            # Submit buttons row
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                submit = st.form_submit_button("Send")
            with col2:
                next_button = st.form_submit_button("Next Step →")
            with col3:
                reset_button = st.form_submit_button("🔄 Reset")
        
        # Process form submission
        if submit and user_input:
            self._handle_message(user_input)
        elif next_button:
            self._handle_next_step()
        elif reset_button:
            self._handle_reset()
    
    def _update_current_step(self):
        """Update current step from chat history."""
        if st.session_state.messages:
            # Extract step number from the most recent assistant message
            for msg in reversed(st.session_state.messages):
                if msg["role"] == "assistant":
                    step_num, total_steps = self._extract_step_number(msg["content"])
                    if step_num is not None:
                        st.session_state.current_step = step_num - 1  # Convert to 0-based index
                        break
    
    def _extract_step_number(self, message):
        """Extract step number from a message."""
        # Look for "Step X of Y" pattern
        step_pattern = r'Step (\d+) of (\d+)'
        match = re.search(step_pattern, message)
        if match:
            try:
                return int(match.group(1)), int(match.group(2))
            except:
                pass
        return None, None
    
    def _get_video_segments(self):
        """Get video segments from knowledge base."""
        kb_data = st.session_state.kb_data
        if not kb_data:
            return []
        
        # Look for video segments in installation methods
        for machine in kb_data.get("machines", []):
            for method in machine.get("installation_methods", []):
                if "videos" in method and method["videos"]:
                    for video in method["videos"]:
                        if "segments" in video:
                            return video["segments"]
        
        # No segments found
        return []
    
    def _time_to_seconds(self, time_str):
        """Convert time string to seconds."""
        if not time_str:
            return 0
            
        parts = time_str.split(':')
        if len(parts) == 2:
            minutes, seconds = map(float, parts)
            return minutes * 60 + seconds
        elif len(parts) == 3:
            hours, minutes, seconds = map(float, parts)
            return hours * 3600 + minutes * 60 + seconds
        else:
            return 0
    
    def _process_actions(self):
        """Process user actions."""
        # Get current concept from latest message
        if st.session_state.messages:
            for msg in reversed(st.session_state.messages):
                if msg["role"] == "assistant":
                    concept = self._get_concept_for_message(msg["content"])
                    if concept:
                        st.session_state.current_concept = concept
                        break
        
    def _handle_message(self, message):
        """Handle user message."""
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": message})
        
        # Process the message
        response = st.session_state.bot.process_message(st.session_state.user_id, message)
        
        # Add assistant message to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Update current step
        self._update_current_step()
        
        # Check for concept relevance - pass both the bot response and user message
        concept = self._get_concept_for_message(response, message)
        if concept:
            st.session_state.current_concept = concept
        
        # Trigger rerun
        st.rerun()
    
    def _handle_next_step(self):
        """Handle next step button."""
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": "[Next Step]"})
        
        # Process the "next" command
        response = st.session_state.bot.process_message(st.session_state.user_id, "next")
        
        # Add assistant message to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Update current step
        self._update_current_step()
        
        # Check for concept relevance
        concept = self._get_concept_for_message(response)
        if concept:
            st.session_state.current_concept = concept
        
        # Trigger rerun
        st.rerun()
    
    def _handle_reset(self):
        """Handle reset button."""
        # Reset the chat
        response = st.session_state.bot.process_message(st.session_state.user_id, "reset")
        st.session_state.messages = [{"role": "assistant", "content": response}]
        st.session_state.current_step = None
        st.session_state.current_segment = None
        st.session_state.current_concept = None
        
        # Trigger rerun
        st.rerun()

def main():
    # Create interface
    interface = EnhancedChatInterface()

if __name__ == "__main__":
    main()