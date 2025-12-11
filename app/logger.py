"""
Corvus XBRL Enterprise - Logging Configuration
Provides structured logging with rotation, levels, and multiple handlers
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional

try:
    from pythonjsonlogger import jsonlogger
    JSON_LOGGER_AVAILABLE = True
except ImportError:
    JSON_LOGGER_AVAILABLE = False


class CorvusLogger:
    """Centralized logging configuration for Corvus XBRL"""

    _instance: Optional['CorvusLogger'] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.log_dir = Path("logs")
            self.log_dir.mkdir(exist_ok=True)
            self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
            self.log_format = os.getenv("LOG_FORMAT", "standard")
            self._initialized = True

    def setup_logger(
        self,
        name: str = "corvus",
        log_file: Optional[str] = None,
        level: Optional[str] = None,
    ) -> logging.Logger:
        """
        Configure and return a logger instance

        Args:
            name: Logger name (typically module name)
            log_file: Optional specific log file path
            level: Optional log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level or self.log_level))

        # Remove existing handlers to avoid duplicates
        logger.handlers.clear()

        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(self._get_formatter("console"))
        logger.addHandler(console_handler)

        # File Handler with Rotation
        if log_file is None:
            log_file = str(self.log_dir / "corvus.log")

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=int(os.getenv("LOG_MAX_BYTES", 10485760)),  # 10MB default
            backupCount=int(os.getenv("LOG_BACKUP_COUNT", 5)),
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(self._get_formatter("file"))
        logger.addHandler(file_handler)

        # Error File Handler (errors only)
        error_file = str(self.log_dir / "corvus_errors.log")
        error_handler = logging.handlers.RotatingFileHandler(
            error_file,
            maxBytes=int(os.getenv("LOG_MAX_BYTES", 10485760)),
            backupCount=int(os.getenv("LOG_BACKUP_COUNT", 5)),
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(self._get_formatter("file"))
        logger.addHandler(error_handler)

        # Prevent propagation to root logger
        logger.propagate = False

        return logger

    def _get_formatter(self, handler_type: str) -> logging.Formatter:
        """Get appropriate formatter based on configuration"""

        if self.log_format == "json" and JSON_LOGGER_AVAILABLE:
            return jsonlogger.JsonFormatter(
                "%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d"
            )

        if handler_type == "console":
            return logging.Formatter(
                "%(levelname)-8s | %(name)-20s | %(message)s",
                datefmt="%H:%M:%S",
            )
        else:
            return logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-20s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

    def get_logger(self, name: str) -> logging.Logger:
        """Get or create a logger for a specific module"""
        return self.setup_logger(name)


# Global logger instance
_corvus_logger = CorvusLogger()


def get_logger(name: str = "corvus") -> logging.Logger:
    """
    Get a configured logger instance

    Usage:
        from app.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Processing XBRL file")
    """
    return _corvus_logger.get_logger(name)


# Module-level convenience functions
def setup_application_logging():
    """Setup logging for the entire application"""
    logger = get_logger("corvus")
    logger.info("=" * 50)
    logger.info("Corvus XBRL Enterprise Starting")
    logger.info(f"Log Level: {_corvus_logger.log_level}")
    logger.info(f"Log Directory: {_corvus_logger.log_dir}")
    logger.info("=" * 50)
    return logger


if __name__ == "__main__":
    # Test logging configuration
    test_logger = get_logger("test")
    test_logger.debug("Debug message")
    test_logger.info("Info message")
    test_logger.warning("Warning message")
    test_logger.error("Error message")
    test_logger.critical("Critical message")
