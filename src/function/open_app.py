"""Backward-compatible import path for the application launcher service."""

from src.services.app_launcher import load_app_paths, load_launch_paths, open_application

__all__ = ["load_app_paths", "load_launch_paths", "open_application"]
