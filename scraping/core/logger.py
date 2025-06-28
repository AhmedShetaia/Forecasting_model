"""
Logger configuration for the application.
"""
import logging
import os
from logging.handlers import RotatingFileHandler


class ScraperLogger:
    """Helper class for managing scraper logging."""

    @staticmethod
    def get_logger(name, log_level=logging.INFO):
        """
        Get a logger with the specified name.

        Args:
            name: Logger name (typically the scraper name)
            log_level: Logging level

        Returns:
            The configured logger
        """
        logger = logging.getLogger(name)

        # Only configure logger if it hasn't been configured already
        if not logger.handlers:
            logger.setLevel(log_level)
            
            # Prevent propagation to avoid duplicate messages
            logger.propagate = False

            # Create formatter
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

            # Create console handler
            console = logging.StreamHandler()
            console.setLevel(log_level)
            console.setFormatter(formatter)
            logger.addHandler(console)

            # Create logs directory if it doesn't exist
            logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
            os.makedirs(logs_dir, exist_ok=True)

            # Create file handler
            file_handler = RotatingFileHandler(
                os.path.join(logs_dir, f"{name}.log"),
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger


# For backwards compatibility
def setup_logging(name=None, log_level=logging.INFO):
    """
    Configure logging for the application.

    Args:
        name: Name of the logger (default: None, uses root logger)
        log_level: Logging level (default: INFO)

    Returns:
        The configured logger
    """
    return ScraperLogger.get_logger(name or "scraper_app", log_level)
