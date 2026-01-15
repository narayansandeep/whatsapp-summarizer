"""
Vercel serverless function entry point
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app_prod import app

# This is what Vercel looks for
handler = app
