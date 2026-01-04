"""
Logging Configuration Example for Secure Media Processor

This module provides a simple logging configuration example that can be used
across the application. It demonstrates how to set up console and file logging
with appropriate formatting and log levels.

Usage:
    import logging
    from logging_config import setup_logging
    
    # Set up logging at application start
    setup_logging(log_level=logging.INFO, log_file='app.log')
    
    # Use logging in your modules
    logger = logging.getLogger(__name__)
    logger.info("Application started")
    logger.error("An error occurred")
"""

import logging
import logging.handlers
import os
from pathlib import Path


def setup_logging(
    log_level=logging.INFO,
    log_file=None,
    log_format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    date_format='%Y-%m-%d %H:%M:%S',
    max_bytes=10485760,  # 10MB
    backup_count=5
):
    """
    Set up logging configuration for the application.
    
    Args:
        log_level: Logging level (e.g., logging.INFO, logging.DEBUG)
        log_file: Optional path to log file. If None, logs only to console.
        log_format: Format string for log messages
        date_format: Format string for timestamps
        max_bytes: Maximum size of log file before rotation (default: 10MB)
        backup_count: Number of backup files to keep
    
    Example:
        # Console logging only
        setup_logging(log_level=logging.INFO)
        
        # Console and file logging
        setup_logging(log_level=logging.DEBUG, log_file='logs/app.log')
        
        # Production configuration
        setup_logging(
            log_level=logging.WARNING,
            log_file='/var/log/secure-media-processor/app.log',
            max_bytes=20971520,  # 20MB
            backup_count=10
        )
    """
    # Create formatter
    formatter = logging.Formatter(log_format, datefmt=date_format)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    root_logger.handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        # Create log directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use rotating file handler to prevent log files from growing too large
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set log level for third-party libraries to reduce noise
    logging.getLogger('boto3').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('google').setLevel(logging.WARNING)
    logging.getLogger('googleapiclient').setLevel(logging.WARNING)
    logging.getLogger('dropbox').setLevel(logging.WARNING)
    
    root_logger.info(f"Logging configured with level: {logging.getLevelName(log_level)}")
    if log_file:
        root_logger.info(f"Log file: {log_file}")


# Example configurations for different environments

def setup_development_logging():
    """Set up logging for development environment."""
    setup_logging(
        log_level=logging.DEBUG,
        log_file='logs/dev.log'
    )


def setup_production_logging():
    """Set up logging for production environment."""
    log_dir = os.getenv('LOG_DIR', '/var/log/secure-media-processor')
    setup_logging(
        log_level=logging.INFO,
        log_file=os.path.join(log_dir, 'app.log'),
        max_bytes=20971520,  # 20MB
        backup_count=10
    )


def setup_testing_logging():
    """Set up logging for testing environment (minimal output)."""
    setup_logging(
        log_level=logging.WARNING
    )


if __name__ == '__main__':
    # Example usage
    print("Logging Configuration Example\n")
    
    # Development setup
    print("1. Development logging:")
    setup_development_logging()
    logger = logging.getLogger(__name__)
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    print("\n2. Production logging:")
    # Uncomment to test production logging
    # setup_production_logging()
    
    print("\n3. Custom logging:")
    # Custom configuration
    setup_logging(
        log_level=logging.INFO,
        log_format='[%(levelname)s] %(name)s: %(message)s',
        log_file='logs/custom.log'
    )
    logger.info("Custom logging format applied")
