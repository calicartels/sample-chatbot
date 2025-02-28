# chatbot/bot.py
"""
Main chatbot implementation for sensor installation guidance.
"""
import json
import re
import os
import vertexai
from vertexai.generative_models import GenerativeModel, Content

from rag.state import StateManager, ConversationStage
from rag.templates import *
from utils.video_processor import VideoProcessor

class InstallationBot:
    """Chatbot for sensor installation guidance."""
    
    def __init__(self, knowledge_base_path, state_storage_path=None, storage_client=None):
        """Initialize the installation bot."""
        self.knowledge_base_path = knowledge_base_path
        self.state_manager = StateManager(state_storage_path)
        self.video_processor = VideoProcessor(storage_client)
        
        # Load knowledge base
        self.knowledge_base = self._load_knowledge_base()
        
        # Prepare video segments
        self.video_segments = {}
        # We'll load these on demand when a specific installation method is selected
        
        # Initialize LLM if available (for enhanced natural language understanding)
        try:
            self.llm = GenerativeModel("gemini-pro")
            self.use_llm = True
            print("✓ Successfully initialized LLM for enhanced understanding")
        except Exception as e:
            print(f"⚠️ LLM initialization failed: {e}")
            print("⚠️ Falling back to pattern matching for user intent recognition")
            self.use_llm = False
    
    def _load_knowledge_base(self):
        """Load knowledge base from file."""
        try:
            with open(self.knowledge_base_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading knowledge base: {e}")
            return {}
    
    def process_message(self, user_id, message):
        """Process a user message and generate a response."""
        # Get conversation state for this user
        state = self.state_manager.get_state(user_id)
        
        # Handle special commands
        if message.lower() == "reset":
            state.reset()
            self.state_manager.save_state(user_id, state)
            return WELCOME_MESSAGE
        
        # Enhanced intent recognition with LLM if available
        intent = None
        if self.use_llm and len(message) > 3:  # Only use LLM for non-trivial messages
            intent = self._get_intent_with_llm(message, state)
        
        # Process message based on current conversation stage
        if state.stage == ConversationStage.WELCOME:
            response = self._handle_welcome(state)
        elif state.stage == ConversationStage.MACHINE_SELECTION:
            response = self._handle_machine_selection(state, message, intent)
        elif state.stage == ConversationStage.CONFIGURATION_SELECTION:
            response = self._handle_configuration(state, message, intent)
        elif state.stage == ConversationStage.ADDITIONAL_INFO:
            response = self._handle_additional_info(state, message, intent)
        elif state.stage == ConversationStage.SENSOR_COUNT:
            response = self._handle_sensor_count(state, message, intent)
        elif state.stage == ConversationStage.RECOMMENDATION:
            response = self._handle_recommendation(state, message, intent)
        elif state.stage == ConversationStage.INSTALLATION_START:
            response = self._handle_installation_start(state, message, intent)
        elif state.stage == ConversationStage.INSTALLATION_STEPS:
            response = self._handle_installation_steps(state, message, intent)
        elif state.stage == ConversationStage.INSTALLATION_COMPLETE:
            response = self._handle_installation_complete(state, message, intent)
        else:
            response = "I'm not sure how to respond to that. Let's start over."
            state.reset()
        
        # Save updated state
        self.state_manager.save_state(user_id, state)
        
        return response
    
    def _get_intent_with_llm(self, message, state):
        """
        Get user intent using LLM.
        
        Args:
            message (str): User message
            state (ConversationState): Current conversation state
            
        Returns:
            dict: Intent information
        """
        try:
            # Create context based on conversation state
            context = f"Current conversation stage: {state.stage.name}\n"
            if state.machine_type:
                context += f"Machine type: {state.machine_type}\n"
            if state.configuration:
                context += f"Configuration: {state.configuration}\n"
            
            # Prepare prompt for intent classification
            prompt = f"""
            As a sensor installation assistant, analyze this user message in the context of our conversation.

            CONTEXT:
            {context}

            USER MESSAGE:
            "{message}"

            Extract the user's intent and any entities. Output ONLY a JSON object with:
            - primary_intent: The main thing the user wants (e.g., "select_machine", "confirm", "request_help", etc.)
            - entities: Any specific items mentioned (e.g., machine types, configurations, numbers)
            - sentiment: positive, negative, or neutral
            - is_affirmative: true if this is clearly an affirmative response, false otherwise
            """
            
            # Get response from LLM
            response = self.llm.generate_content(prompt)
            
            # Parse the response into a dict
            intent_text = response.text
            
            # Extract JSON from response
            intent_match = re.search(r'{.*}', intent_text, re.DOTALL)
            if intent_match:
                intent_json = intent_match.group(0)
                try:
                    return json.loads(intent_json)
                except:
                    print(f"Error parsing intent JSON: {intent_json}")
            
            return None
        
        except Exception as e:
            print(f"Error getting intent with LLM: {e}")
            return None
        
    def _handle_welcome(self, state):
        """Handle welcome stage."""
        state.advance_stage()
        return WELCOME_MESSAGE
    
    def _handle_machine_selection(self, state, message, intent=None):
        """Handle machine type selection."""
        # Try to get machine type from intent first
        machine_type = None
        if intent and "entities" in intent:
            entities = intent.get("entities", {})
            if isinstance(entities, dict) and "machine_type" in entities:
                machine_type = entities["machine_type"]
            elif isinstance(entities, list):
                for entity in entities:
                    if isinstance(entity, dict) and entity.get("type") == "machine_type":
                        machine_type = entity.get("value")
        
        # Fall back to pattern matching if needed
        if not machine_type:
            machine_type = self._extract_machine_type(message)
        
        if not machine_type:
            return MACHINE_TYPE_ERROR
        
        state.machine_type = machine_type
        state.advance_stage()
        
        # Return appropriate prompt for the machine type
        if machine_type == "Fan":
            return FAN_CONFIGURATION_PROMPT
        elif machine_type == "Motor":
            return MOTOR_CONFIGURATION_PROMPT
        elif machine_type == "Pump":
            return PUMP_CONFIGURATION_PROMPT
        else:
            return f"Please specify the configuration for your {machine_type}."
    
    def _handle_configuration(self, state, message, intent=None):
        """Handle configuration selection."""
        # Try to get configuration from intent first
        configuration = None
        if intent and "entities" in intent:
            entities = intent.get("entities", {})
            if isinstance(entities, dict) and "configuration" in entities:
                configuration = entities["configuration"]
            elif isinstance(entities, list):
                for entity in entities:
                    if isinstance(entity, dict) and entity.get("type") == "configuration":
                        configuration = entity.get("value")
        
        # Fall back to pattern matching if needed
        if not configuration:
            configuration = self._extract_configuration(message)
        
        if not configuration:
            return CONFIGURATION_ERROR.format(machine_type=state.machine_type)
        
        state.configuration = configuration
        state.advance_stage()
        
        return ORIENTATION_PROMPT.format(machine_type=state.machine_type)
    
    def _handle_additional_info(self, state, message, intent=None):
        """Handle orientation and RPM collection."""
        if not state.orientation:
            # Try to get orientation from intent first
            orientation = None
            if intent and "entities" in intent:
                entities = intent.get("entities", {})
                if isinstance(entities, dict) and "orientation" in entities:
                    orientation = entities["orientation"]
                elif isinstance(entities, list):
                    for entity in entities:
                        if isinstance(entity, dict) and entity.get("type") == "orientation":
                            orientation = entity.get("value")
            
            # Fall back to pattern matching if needed
            if not orientation:
                orientation = self._extract_orientation(message)
            
            if not orientation:
                return ORIENTATION_ERROR.format(machine_type=state.machine_type)
            
            state.orientation = orientation
            return RPM_PROMPT.format(machine_type=state.machine_type)
        
        # Handle RPM input if orientation is already set
        # Try to get RPM from intent first
        rpm = None
        if intent and "entities" in intent:
            entities = intent.get("entities", {})
            if isinstance(entities, dict) and "number" in entities:
                rpm = entities["number"]
            elif isinstance(entities, list):
                for entity in entities:
                    if isinstance(entity, dict) and entity.get("type") == "number":
                        rpm = entity.get("value")
        
        # Fall back to pattern matching if needed
        if not rpm:
            rpm = self._extract_rpm(message)
        
        if not rpm:
            return RPM_ERROR
        
        state.rpm = rpm
        state.advance_stage()
        
        return SENSOR_COUNT_PROMPT
    
    def _handle_sensor_count(self, state, message, intent=None):
        """Handle sensor count collection."""
        # Try to get sensor count from intent first
        sensor_count = None
        if intent and "entities" in intent:
            entities = intent.get("entities", {})
            if isinstance(entities, dict) and "number" in entities:
                sensor_count = entities["number"]
            elif isinstance(entities, list):
                for entity in entities:
                    if isinstance(entity, dict) and entity.get("type") == "number":
                        sensor_count = entity.get("value")
        
        # Fall back to pattern matching if needed
        if not sensor_count:
            sensor_count = self._extract_number(message)
        
        if not sensor_count:
            return SENSOR_COUNT_ERROR
        
        state.sensor_count = sensor_count
        state.advance_stage()
        
        return MONITORING_TARGET_PROMPT
    
    def _handle_recommendation(self, state, message, intent=None):
        """Handle recommendation phase."""
        if not state.monitoring_target:
            # Try to get monitoring target from intent first
            monitoring_target = None
            if intent and "entities" in intent:
                entities = intent.get("entities", {})
                if isinstance(entities, dict) and "monitoring_target" in entities:
                    monitoring_target = entities["monitoring_target"]
                elif isinstance(entities, list):
                    for entity in entities:
                        if isinstance(entity, dict) and entity.get("type") == "monitoring_target":
                            monitoring_target = entity.get("value")
            
            # Fall back to pattern matching if needed
            if not monitoring_target:
                monitoring_target = self._extract_monitoring_target(message)
            
            # Check for negative responses like "no" or "nope" and handle them as "General"
            is_negative = self._is_negative(message)
            if is_negative:
                monitoring_target = "General"
            
            state.monitoring_target = monitoring_target or "General"
            
            # Generate placement recommendations based on machine type and configuration
            if state.configuration == "Direct/Close Coupled":
                ideal_count = 3
                
                # Basic recommendations always include Motor DE
                recommendations = ["Motor Drive-End (DE) - HIGHEST PRIORITY"]
                
                # Add more recommendations based on available sensors
                if state.sensor_count >= 2:
                    recommendations.append("Motor Non-Drive-End (NDE) - For motors ≥ 150 hp")
                
                if state.sensor_count >= 3:
                    recommendations.append("Fan shaft bearings (if accessible)")
                
                state.recommended_placement = recommendations
                
                recommendation_text = RECOMMENDATION_TEMPLATE.format(
                    configuration=state.configuration,
                    machine_type=state.machine_type,
                    ideal_count=ideal_count,
                    sensor_count=state.sensor_count,
                    recommendations="\n\n".join([f"{i+1}. {rec}" for i, rec in enumerate(recommendations)])
                )
                return recommendation_text
                
            elif state.configuration == "Belt Driven":
                # Similar logic for Belt Driven configuration
                ideal_count = 4
                
                # Basic recommendations always include Motor DE
                recommendations = ["Motor Drive-End (DE) - HIGHEST PRIORITY"]
                recommendation_details = [
                    "This bearing experiences the most load and stress, making it critical for monitoring."
                ]
                
                # Add more recommendations based on available sensors
                if state.sensor_count >= 2:
                    recommendations.append("Motor Non-Drive-End (NDE) - For motors ≥ 150 hp")
                    recommendation_details.append(
                        "Larger motors benefit from monitoring both ends for a complete vibration profile."
                    )
                
                if state.sensor_count >= 3:
                    recommendations.append("Belt-Side bearing")
                    recommendation_details.append(
                        "This bearing transfers power from motor to fan, critical for early fault detection."
                    )
                
                if state.sensor_count >= 4:
                    recommendations.append("Fan-Side bearing")
                    recommendation_details.append(
                        "Supports fan shaft, important for complete system coverage."
                    )
                
                state.recommended_placement = recommendations
                
                # Create formatted recommendation text with details
                rec_text = ""
                for i, (rec, detail) in enumerate(zip(recommendations, recommendation_details)):
                    rec_text += f"{i+1}. {rec}\n   {detail}\n\n"
                
                recommendation_text = RECOMMENDATION_TEMPLATE.format(
                    configuration=state.configuration,
                    machine_type=state.machine_type,
                    ideal_count=ideal_count,
                    sensor_count=state.sensor_count,
                    recommendations=rec_text.strip()
                )
                return recommendation_text
            else:
                # Generic recommendation for other configurations
                return f"""
Based on your {state.configuration} configuration, I recommend placing your {state.sensor_count} sensor(s) on the most critical components for monitoring.

Would you like to proceed with the installation instructions?
"""
        
        # Check if user wants to proceed with installation
        # First check intent from LLM if available
        is_affirmative = False
        if intent and "is_affirmative" in intent:
            is_affirmative = intent["is_affirmative"]
        
        # Fall back to pattern matching
        if not is_affirmative:
            is_affirmative = self._is_affirmative(message)
        
        if is_affirmative:
            # User wants to proceed with installation
            state.advance_stage()
            # Find the best installation method based on configuration
            method = "Drill and Tap"  # Default
            for machine in self.knowledge_base.get("machines", []):
                for installation_method in machine.get("installation_methods", []):
                    if "name" in installation_method and installation_method.get("name") == "Drill and Tap":
                        method = installation_method.get("name")
                        break
            
            return INSTALLATION_METHOD_PROMPT.format(
                machine_type=state.machine_type,
                recommended_method=method
            )
        else:
            # Ask again about specific part
            state.monitoring_target = None
            return MONITORING_TARGET_PROMPT
    
    def _handle_installation_start(self, state, message, intent=None):
        """Handle installation method selection and start."""
        if not state.installation_method:
            # Check intent from LLM if available
            chosen_method = None
            if intent and "entities" in intent:
                entities = intent.get("entities", {})
                if isinstance(entities, dict) and "installation_method" in entities:
                    chosen_method = entities["installation_method"]
                elif isinstance(entities, list):
                    for entity in entities:
                        if isinstance(entity, dict) and entity.get("type") == "installation_method":
                            chosen_method = entity.get("value")
            
            # Fall back to pattern matching
            if not chosen_method:
                if "yes" in message.lower() or "drill" in message.lower() or "tap" in message.lower():
                    chosen_method = "Drill and Tap"
                elif "epoxy" in message.lower() or "adhesive" in message.lower():
                    chosen_method = "Epoxy Mount"
                elif "magnet" in message.lower():
                    chosen_method = "Magnets"
                elif "adapter" in message.lower():
                    chosen_method = "Other Adapter Options"
            
            if not chosen_method:
                return "Please select an installation method: Drill and Tap (recommended), Epoxy Mount, Other Adapter Options, or Magnets."
            
            state.installation_method = chosen_method
            
            # Prepare video segments for the selected method
            self.video_segments = self.video_processor.prepare_segments_from_kb(
                self.knowledge_base, 
                state.installation_method
            )
            
            # Get materials needed for the selected method
            materials = INSTALLATION_MATERIALS.get(state.installation_method, 
                ["Sensor and necessary installation tools"])
            
            materials_text = "\n".join([f"- {m}" for m in materials])
            
            return INSTALLATION_START_TEMPLATE.format(
                method=state.installation_method,
                materials=materials_text
            )
        
        # Process response to installation intro
        # Check intent from LLM if available
        wants_video = False
        wants_steps = False
        
        if intent and "primary_intent" in intent:
            primary_intent = intent["primary_intent"]
            wants_video = "video" in primary_intent.lower()
            wants_steps = "step" in primary_intent.lower() or "guide" in primary_intent.lower()
        
        # Fall back to pattern matching
        if not wants_video and not wants_steps:
            wants_video = "full video" in message.lower() or "show video" in message.lower()
            wants_steps = "step by step" in message.lower() or "guide" in message.lower()
        
        if wants_video:
            # Show full installation video
            if "full" in self.video_segments:
                full_video = self.video_segments["full"]
                state.advance_stage()
                state.current_step = 1  # Start with first step
                
                return FULL_VIDEO_TEMPLATE.format(
                    duration=full_video.get("duration", "1:41"),
                    video_path=full_video["video_path"]
                )
            else:
                # No full video available, fall back to step-by-step
                state.advance_stage()
                state.current_step = 1
                return self._get_step_guidance(state.installation_method, 1)
        elif wants_steps or self._is_affirmative(message):
            # Start step by step guidance
            state.advance_stage()
            state.current_step = 1
            return self._get_step_guidance(state.installation_method, 1)
        else:
            # Unclear response
            return "Would you like to see the full installation video, or shall we proceed step by step?"
    
    def _handle_installation_steps(self, state, message, intent=None):
        """Handle installation steps guidance."""
        # Check for help request with specific step
        # Check intent from LLM if available
        wants_video = False
        needs_help = False
        wants_next = False
        
        if intent and "primary_intent" in intent:
            primary_intent = intent["primary_intent"]
            wants_video = "video" in primary_intent.lower() or "show" in primary_intent.lower()
            needs_help = "help" in primary_intent.lower() or "problem" in primary_intent.lower()
            wants_next = "next" in primary_intent.lower() or "continue" in primary_intent.lower() or "ready" in primary_intent.lower()
        
        # Fall back to pattern matching
        if wants_video or "video" in message.lower() or "show me" in message.lower():
            step_reference = state.current_step
            
            # Check if we have a video segment for this step
            if step_reference in self.video_segments:
                segment = self.video_segments[step_reference]
                
                return VIDEO_SEGMENT_TEMPLATE.format(
                    title=segment["title"],
                    start_time=segment["start_time"],
                    end_time=segment["end_time"],
                    video_path=segment["video_path"]
                )
            else:
                # If no specific segment, offer the full video
                if "full" in self.video_segments:
                    full_video = self.video_segments["full"]
                    
                    return f"""
I don't have a specific video for just this step, but you can watch the full installation video and skip to around {self._get_timestamp_for_step(state.current_step)}:

[VIDEO: {full_video["video_path"]}]

Does this help?
"""
                else:
                    return "I'm sorry, I don't have a video available for this step. Would you like more detailed instructions?"
        
        # Handle help request
        elif needs_help or "help" in message.lower() or "issue" in message.lower() or "problem" in message.lower():
            # User needs help with current step
            state.add_issue(f"Needed help with step {state.current_step}")
            
            return HELP_OPTIONS_MESSAGE
        
        # Handle escalation request
        elif "proaxion" in message.lower() or "support" in message.lower() or "expert" in message.lower():
            return SUPPORT_ESCALATION_MESSAGE
        
        # Check if ready for next step
        elif wants_next or self._is_affirmative(message) or "next" in message.lower() or "ready" in message.lower():
            # Move to next step
            total_steps = self._get_total_steps(state.installation_method)
            state.current_step += 1
            
            # Check if all steps completed
            if state.current_step > total_steps:
                state.installation_complete = True
                state.advance_stage()
                
                return INSTALLATION_COMPLETE_MESSAGE.format(method=state.installation_method)
            else:
                # Get next step guidance
                return self._get_step_guidance(state.installation_method, state.current_step)
        else:
            # Unclear response, repeat current step
            return self._get_step_guidance(state.installation_method, state.current_step)
    
    def _handle_installation_complete(self, state, message, intent=None):
        """Handle installation completion."""
        # Check intent from LLM if available
        is_successful = False
        has_issue = False
        
        if intent:
            if "is_affirmative" in intent:
                is_successful = intent["is_affirmative"]
            if "primary_intent" in intent:
                has_issue = "issue" in intent["primary_intent"].lower() or "problem" in intent["primary_intent"].lower()
        
        # Fall back to pattern matching
        if not is_successful and not has_issue:
            is_successful = "yes" in message.lower() or "working" in message.lower()
            has_issue = "issue" in message.lower() or "problem" in message.lower() or "not working" in message.lower()
        
        if is_successful:
            # Installation successful
            return SUCCESSFUL_INSTALLATION_MESSAGE
        
        elif has_issue:
            # User has an issue
            state.add_issue("Issue after installation")
            
            # Create specific issues text
            issues_text = "\n".join([f"- {issue}" for issue in state.issues])
            
            return INSTALLATION_ISSUE_MESSAGE.format(specific_issues=issues_text)
        else:
            # Unclear response
            return "Is your sensor working correctly? If you're experiencing any issues, I can connect you with ProAxion support for assistance."
    
    def _get_step_guidance(self, method, step_number):
        """Get guidance for a specific installation step."""
        # Get steps for the selected method from knowledge base
        steps = []
        for machine in self.knowledge_base.get("machines", []):
            for installation_method in machine.get("installation_methods", []):
                if installation_method.get("name") == method:
                    if "steps" in installation_method and installation_method["steps"]:
                        # Extract the actual step descriptions
                        step_descriptions = installation_method["steps"][0].get("description", [])
                        steps = step_descriptions
                        break
        
        # If no steps found or step number out of range, provide generic guidance
        if not steps or step_number > len(steps):
            return STEP_GUIDANCE_TEMPLATE.format(
                step_number=step_number,
                total_steps=max(6, step_number + 2),  # Estimate if unknown
                step_title=f"Continue Installation - Step {step_number}",
                step_description="Please continue following the installation procedure according to the manufacturer's guidelines."
            )
        
        # Get the requested step
        step = steps[step_number - 1]
        
        return STEP_GUIDANCE_TEMPLATE.format(
            step_number=step_number,
            total_steps=len(steps),
            step_title=step.get('title', f'Step {step_number}'),
            step_description=step.get('description', '')
        )
    
    def _get_total_steps(self, method):
        """Get the total number of steps for an installation method."""
        for machine in self.knowledge_base.get("machines", []):
            for installation_method in machine.get("installation_methods", []):
                if installation_method.get("name") == method:
                    if "steps" in installation_method and installation_method["steps"]:
                        return len(installation_method["steps"][0].get("description", []))
        
        return 6  # Default fallback
    
    def _get_timestamp_for_step(self, step_number):
        """Estimate timestamp in the video for a given step."""
        # This is a simple estimation based on the step number
        # In a real implementation, you would use actual timestamps from the knowledge base
        if step_number == 1:
            return "0:09"
        elif step_number == 2:
            return "0:20"
        elif step_number == 3:
            return "0:38"
        elif step_number in [4, 5]:
            return "0:50"
        else:
            return "1:24"
    
    def _extract_machine_type(self, message):
        """Extract machine type from message."""
        message = message.lower()
        
        if "fan" in message:
            return "Fan"
        elif "motor" in message:
            return "Motor"
        elif "pump" in message:
            return "Pump"
        
        return None
    
    def _extract_configuration(self, message):
        """Extract configuration from message."""
        message = message.lower()
        
        if "belt" in message:
            return "Belt Driven"
        elif "direct" in message or "close" in message or "coupled" in message:
            return "Direct/Close Coupled"
        elif "independent" in message or "bearing" in message:
            return "Independent Bearing"
        
        return None
    
    def _extract_orientation(self, message):
        """Extract orientation from message."""
        message = message.lower()
        
        if "center" in message:
            return "Center Hung"
        elif "over" in message:
            return "Overhung"
        
        return None
    
    def _extract_rpm(self, message):
        """Extract RPM from message."""
        match = re.search(r'(\d+)', message)
        if match:
            return int(match.group(1))
        return None
    
    def _extract_number(self, message):
        """Extract a number from message."""
        match = re.search(r'(\d+)', message)
        if match:
            return int(match.group(1))
        return None
    
    def _extract_monitoring_target(self, message):
        """Extract monitoring target from message."""
        message = message.lower()
        
        if "motor" in message:
            return "Motor"
        elif "bearing" in message:
            return "Bearing"
        elif "fan" in message and "housing" in message:
            return "Fan Housing"
        elif "fan" in message:
            return "Fan"
        elif "general" in message:
            return "General"
        
        return None
    
    def _is_affirmative(self, message):
        """Check if message is affirmative."""
        affirmatives = ["yes", "yeah", "sure", "ok", "okay", "ready", "proceed", "continue", "yep", "correct", "right", "good", "fine", "true", "y", "yup", "absolutely"]
        message = message.lower()
        
        return any(word in message for word in affirmatives)
    
    def _is_negative(self, message):
        """Check if message is negative."""
        negatives = ["no", "nope", "nah", "not", "none", "don't", "dont", "negative", "n", "false"]
        message = message.lower()
        
        return any(word in message for word in negatives)
    
    def _format_video_reference(self, video_path):
        """Format a video reference for including in messages."""
        # Ensure the video exists
        if os.path.exists(video_path):
            return f"[VIDEO: {video_path}]"
        else:
            print(f"Warning: Video file not found: {video_path}")
            return f"[VIDEO NOT FOUND: {video_path}]"

    def _get_step_guidance(self, method, step_number):
        """Get guidance for a specific installation step."""
        # Get steps for the selected method from knowledge base
        steps = []
        for machine in self.knowledge_base.get("machines", []):
            for installation_method in machine.get("installation_methods", []):
                if installation_method.get("name") == method:
                    if "steps" in installation_method and installation_method["steps"]:
                        # Extract the actual step descriptions
                        step_descriptions = installation_method["steps"][0].get("description", [])
                        steps = step_descriptions
                        break
        
        # If no steps found or step number out of range, provide generic guidance
        if not steps or step_number > len(steps):
            return STEP_GUIDANCE_TEMPLATE.format(
                step_number=step_number,
                total_steps=max(6, step_number + 2),  # Estimate if unknown
                step_title=f"Continue Installation - Step {step_number}",
                step_description="Please continue following the installation procedure according to the manufacturer's guidelines."
            )
        
        # Get the requested step
        step = steps[step_number - 1]
        
        # Check if we have a video segment for this step
        video_reference = ""
        if step_number in self.video_segments:
            segment = self.video_segments[step_number]
            video_reference = self._format_video_reference(segment["video_path"])
        
        response = STEP_GUIDANCE_TEMPLATE.format(
            step_number=step_number,
            total_steps=len(steps),
            step_title=step.get('title', f'Step {step_number}'),
            step_description=step.get('description', '')
        )
        
        # Add video reference if available
        if video_reference:
            response += f"\n\n{video_reference}"
        
        return response