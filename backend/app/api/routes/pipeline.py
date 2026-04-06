"""
Pipeline API Routes — Re-exports from pipeline/routes.py.

This module re-exports the pipeline router so it can be registered
in main.py alongside other route modules in api/routes/.
"""

from app.pipeline.routes import router

__all__ = ["router"]
