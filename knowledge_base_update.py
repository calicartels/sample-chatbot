#!/usr/bin/env python3
"""
Knowledge Base Update Script

This script updates the knowledge base to add concept-to-image associations
without modifying the existing video information and structure.
"""
import os
import json
import sys
from datetime import datetime

# Add parent directory to system path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from config import STRUCTURED_DIR

def update_knowledge_base():
    """Update the knowledge base with image concept associations."""
    # Find the latest knowledge base file
    kb_files = [f for f in os.listdir(STRUCTURED_DIR) if f.startswith('kb_') and f.endswith('.json')]
    if not kb_files:
        print("No knowledge base files found")
        return False
    
    latest_kb_file = max(kb_files, key=lambda f: os.path.getmtime(os.path.join(STRUCTURED_DIR, f)))
    kb_path = os.path.join(STRUCTURED_DIR, latest_kb_file)
    
    print(f"Updating knowledge base: {kb_path}")
    
    # Load the knowledge base
    with open(kb_path, 'r') as f:
        kb_data = json.load(f)
    
    # Create backup
    backup_path = kb_path.replace('.json', f'_backup_{datetime.now().strftime("%Y%m%d%H%M%S")}.json')
    with open(backup_path, 'w') as f:
        json.dump(kb_data, f, indent=2)
    
    print(f"Created backup at: {backup_path}")
    
    # Define image associations for concepts
    image_associations = {
        "center_hung_vs_overhung": [
            "1k1I7_tVuTaRePPTirBd8qybUFxQlemVqsr0SFlXo4RU_inline_kix.psd2ci67xg6x.jpg",
            "1k1I7_tVuTaRePPTirBd8qybUFxQlemVqsr0SFlXo4RU_inline_kix.oii21q7a0sh4.jpg"
        ],
        "direct_coupled_fan": [
            "1k1I7_tVuTaRePPTirBd8qybUFxQlemVqsr0SFlXo4RU_inline_kix.6lr2lt73t04n.jpg",
            "1k1I7_tVuTaRePPTirBd8qybUFxQlemVqsr0SFlXo4RU_inline_kix.q4g0mttrmf6r.jpg"
        ],
        "belt_driven_fan": [
            "1k1I7_tVuTaRePPTirBd8qybUFxQlemVqsr0SFlXo4RU_inline_kix.imw6npqb9mbt.jpg",
            "1k1I7_tVuTaRePPTirBd8qybUFxQlemVqsr0SFlXo4RU_inline_kix.t0c3ao4pcqvh.jpg"
        ],
        "drill_and_tap": [
            "1k1I7_tVuTaRePPTirBd8qybUFxQlemVqsr0SFlXo4RU_inline_kix.cz2aqqk57l6e.jpg",
            "1k1I7_tVuTaRePPTirBd8qybUFxQlemVqsr0SFlXo4RU_inline_kix.6rzrpubt0i5j.jpg"
        ],
        "epoxy_mount": [
            "1k1I7_tVuTaRePPTirBd8qybUFxQlemVqsr0SFlXo4RU_inline_kix.f7y4f33869jw.jpg",
            "1k1I7_tVuTaRePPTirBd8qybUFxQlemVqsr0SFlXo4RU_inline_kix.v6z5r82ijyz6.jpg"
        ],
        "sensor_installation": [
            "1k1I7_tVuTaRePPTirBd8qybUFxQlemVqsr0SFlXo4RU_inline_kix.j9zpqei17lf2.jpg",
            "1k1I7_tVuTaRePPTirBd8qybUFxQlemVqsr0SFlXo4RU_inline_kix.seh4nr1xvd0j.jpg",
            "1k1I7_tVuTaRePPTirBd8qybUFxQlemVqsr0SFlXo4RU_inline_kix.2n8hbictzvg.jpg"
        ]
    }
    
    # Add concept explanations with image references
    concept_explanations = {
        "center_hung_vs_overhung": {
            "center_hung": "Center hung fans have support bearings on both sides of the fan wheel, providing balanced support. This configuration is common in larger fans where stability is crucial.",
            "overhung": "Overhung fans have the fan wheel mounted on one end of the shaft with support only on one side. This design is more compact but may experience more vibration."
        },
        "direct_coupled_fan": {
            "description": "Direct/Close Coupled fans feature a direct connection between the motor and fan shafts without any intermediary coupling. This configuration provides high efficiency, simple design, and compact size.",
            "key_points": "High efficiency, simple design, compact size, limited speed adjustment options",
            "sensor_placement": "Motor DE (Drive End) - Highest priority, Motor NDE (Non-Drive End) for larger motors (>150hp), Fan shaft bearings (if accessible)"
        },
        "belt_driven_fan": {
            "description": "Belt Driven fans use belts and pulleys to connect the motor and fan. This configuration allows for speed adjustments and easier maintenance access.",
            "key_points": "Flexibility in speed control, easier maintenance due to accessibility, may require more space, belt maintenance required",
            "sensor_placement": "Motor DE (Drive End) - Highest priority, Motor NDE (Non-Drive End) for larger motors (>150hp), Belt-Side bearing, Fan-Side bearing"
        },
        "installation_methods": {
            "drill_and_tap": "The Drill and Tap method creates a threaded hole directly in the machine surface for mounting sensors. This provides the most secure and accurate connection.",
            "epoxy_mount": "Epoxy mounting uses industrial adhesive to attach sensors to surfaces where drilling isn't possible or desired.",
            "magnets": "Magnetic mounts provide quick temporary installation but are not recommended for permanent vibration monitoring due to potential movement."
        }
    }
    
    # Add image associations to the knowledge base
    kb_data["image_associations"] = image_associations
    
    # Add concept explanations to the knowledge base
    kb_data["concept_explanations"] = concept_explanations
    
    # Save updated knowledge base
    with open(kb_path, 'w') as f:
        json.dump(kb_data, f, indent=2)
    
    print(f"Knowledge base updated successfully. Added:")
    print(f"- Image associations for {len(image_associations)} concepts")
    print(f"- Explanations for {len(concept_explanations)} concepts")
    print(f"Original backed up to {backup_path}")
    
    # Verify that video segments are still present (Fixed for your structure)
    videos_found = False
    
    # Check the exact structure in your knowledge base
    if "machines" in kb_data:
        for machine in kb_data["machines"]:
            if "installation_methods" in machine:
                for method in machine["installation_methods"]:
                    if "videos" in method and method["videos"]:
                        videos_found = True
                        print(f"✓ Video data preserved for {method['name']} method")
                        # Print segments
                        segments = method["videos"][0].get("segments", [])
                        if segments:
                            print(f"  Found {len(segments)} video segments")
    
    if not videos_found:
        print("⚠️ No video data found in the knowledge base")
        print("⚠️ Adding video information structure")
        
        # Try to find Drill and Tap method and add video information
        for machine in kb_data.get("machines", []):
            for method in machine.get("installation_methods", []):
                if method.get("name") == "Drill and Tap":
                    # Add video information
                    method["videos"] = [
                        {
                            "id": "sensor_installation_drill_tap",
                            "title": "Sensor Installation: Drill & Tap Method",
                            "uri": "gs://proaxionsample/sample/Videos/sensor_installation_drill_tap.mp4",
                            "duration": "1:41",
                            "segments": [
                                {
                                    "start": "0:05",
                                    "end": "0:07", 
                                    "title": "Materials Required",
                                    "description": "Overview of tools and materials needed for installation",
                                    "step_reference": 0
                                },
                                {
                                    "start": "0:09",
                                    "end": "0:38",
                                    "title": "Surface Preparation",
                                    "description": "Creating a pilot hole and preparing the mounting surface",
                                    "step_reference": 1
                                },
                                {
                                    "start": "0:38",
                                    "end": "0:46",
                                    "title": "Tapping the Hole",
                                    "description": "Using a thread tap to create screw threads",
                                    "step_reference": 2
                                },
                                {
                                    "start": "0:50",
                                    "end": "1:05",
                                    "title": "Applying Thread Locker",
                                    "description": "Preparing the sensor with thread locker",
                                    "step_reference": 3
                                },
                                {
                                    "start": "1:05",
                                    "end": "1:21",
                                    "title": "Applying Silicone Sealant",
                                    "description": "Adding sealant to prevent corrosion",
                                    "step_reference": 4
                                },
                                {
                                    "start": "1:24",
                                    "end": "1:41",
                                    "title": "Hand-Tightening the Sensor",
                                    "description": "Final installation of the sensor",
                                    "step_reference": 5
                                }
                            ]
                        }
                    ]
                    print("✓ Added video data to Drill and Tap method")
                    
                    # Save updated knowledge base with video data
                    with open(kb_path, 'w') as f:
                        json.dump(kb_data, f, indent=2)
                    
                    videos_found = True
                    break
            if videos_found:
                break
    
    return True

if __name__ == "__main__":
    update_knowledge_base()