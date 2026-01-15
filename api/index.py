"""
Vercel serverless function entry point for Flask
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import the Flask app
from app_flask import app

# Vercel expects 'app' to be the Flask application object
# No wrapper needed - Flask works directly with Vercel
