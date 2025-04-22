"""Logging module for the LLM Security Firewall."""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional

from src.config import settings


def setup_logger(
    name: str, level: Optional[str] = None, file_path: Optional[str] = None
) -> logging.Logger:
    """Set up and configure a logger.

    Args:
        name: The name of the logger.
        level: The logging level. Defaults to the level in settings.
        file_path: The path to the log file. Defaults to the path in settings.

    Returns:
        The configured logger.
    """
    logger = logging.getLogger(name)
    
    # Set log level
    log_level = level or settings.logging.level
    logger.setLevel(getattr(logging, log_level))
    
    # Create formatter
    formatter = logging.Formatter(settings.logging.format)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if file path is provided
    log_file = file_path or settings.logging.file_path
    if log_file:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Create rotating file handler
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# Create global logger instance
logger = setup_logger("llm_security_firewall")
