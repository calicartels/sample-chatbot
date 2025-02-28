#!/usr/bin/env python3
"""
Script to run both the FastAPI backend and Streamlit frontend.
"""
import os
import sys
import subprocess
import time
import threading
import webbrowser
import argparse

def run_backend():
    """Run the FastAPI backend."""
    print("Starting FastAPI backend on http://localhost:8000...")
    
    # Use uvicorn to run the FastAPI app
    command = [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    subprocess.run(command)

def run_frontend():
    """Run the Streamlit frontend."""
    print("Starting Streamlit frontend on http://localhost:8501...")
    
    # Use streamlit to run the frontend app
    command = [sys.executable, "-m", "streamlit", "run", "frontend/app.py"]
    subprocess.run(command)

def open_browser():
    """Open the browser after a short delay."""
    time.sleep(3)  # Give the servers time to start
    webbrowser.open("http://localhost:8501")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Run the ProAxion Sensor Installation web application")
    parser.add_argument("--backend-only", action="store_true", help="Run only the backend")
    parser.add_argument("--frontend-only", action="store_true", help="Run only the frontend")
    parser.add_argument("--no-browser", action="store_true", help="Don't open the browser automatically")
    
    args = parser.parse_args()
    
    if args.backend_only:
        run_backend()
    elif args.frontend_only:
        run_frontend()
    else:
        # Run both backend and frontend in separate threads
        backend_thread = threading.Thread(target=run_backend)
        frontend_thread = threading.Thread(target=run_frontend)
        
        # Start the threads
        backend_thread.start()
        frontend_thread.start()
        
        # Open the browser if not disabled
        if not args.no_browser:
            browser_thread = threading.Thread(target=open_browser)
            browser_thread.start()
        
        # Wait for the threads to finish
        backend_thread.join()
        frontend_thread.join()

if __name__ == "__main__":
    main()