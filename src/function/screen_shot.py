"""Backward-compatible import path for the screenshot service."""

from src.services.screenshot import capture_screen_content

__all__ = ["capture_screen_content"]
