"""Tests for the logger module."""

import logging
import os
from src.logger import setup_logger

def test_setup_logger():
    """Test that setup_logger configures the logging system correctly."""
    # Setup logger with default settings
    test_logger = setup_logger("test_logger")

    # Test that the logger is properly configured
    assert test_logger is not None
    assert isinstance(test_logger, logging.Logger)

    # Get the root logger
    root_logger = logging.getLogger()

    # Test that the root logger has at least one handler
    assert len(root_logger.handlers) > 0

    # Test that the log level is set
    assert root_logger.level in [
        logging.DEBUG,
        logging.INFO,
        logging.WARNING,
        logging.ERROR,
        logging.CRITICAL
    ]

def test_logger_name():
    """Test that setup_logger returns a properly named logger."""
    # Get a logger for a specific module
    logger = setup_logger("test_module")

    # Test that the logger is an instance of logging.Logger
    assert isinstance(logger, logging.Logger)

    # Test that the logger name is correct
    assert logger.name == "test_module"

    # 测试日志级别是否有效
    assert logger.level in [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]

def test_log_to_file(tmpdir):
    """Test that logs are written to a file."""
    # Create a temporary log file
    log_file = os.path.join(tmpdir, "test.log")

    # Setup logger with the temporary file
    logger = setup_logger("test_file_logger", file_path=log_file)

    # Log a message
    test_message = "This is a test log message"
    logger.info(test_message)

    # Check that the log file exists and contains the message
    assert os.path.exists(log_file)
    with open(log_file, "r") as f:
        log_content = f.read()
        assert test_message in log_content

def test_log_levels():
    """Test that different log levels work correctly."""
    # Setup logger
    logger = setup_logger("test_levels")

    # Test each log level
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")

    # No assertions here, just making sure no exceptions are raised
