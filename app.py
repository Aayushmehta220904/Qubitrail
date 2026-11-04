"""Vercel-recognized FastAPI entrypoint.

Local development continues to work with `python run.py`.
"""
from backend.main import app

__all__ = ["app"]
