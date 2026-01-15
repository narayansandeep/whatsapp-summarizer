"""
Vercel serverless function entry point for Flask
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app_flask import app

# Flask app is the handler
# Vercel will automatically use the Flask app
handler = app
