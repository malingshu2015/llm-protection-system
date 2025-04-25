"""Local LLM Protection System package."""

import os

# Get version from VERSION file
VERSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "VERSION")
__version__ = "1.0.0"  # Default version
if os.path.exists(VERSION_FILE):
    with open(VERSION_FILE, "r") as f:
        __version__ = f.read().strip()

__all__ = ["__version__"]
