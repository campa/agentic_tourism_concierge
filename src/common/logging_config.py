import logging
import logging.config

# Centralized logging configuration for the entire project
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "rich": {
            "format": "%(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    },
    "handlers": {
        "console": {
            "class": "rich.logging.RichHandler",
            "level": "DEBUG",
            "formatter": "rich",
            "show_time": True,
            "show_level": True,
            "show_path": False,
            "markup": True,
        }
    },
    "loggers": {
        # Personal Information Collector
        "personal_information_collector": {"level": "DEBUG"},
        # Holiday Information Collector
        "holiday_information_collector": {"level": "DEBUG"},
        # Product Screening Pipeline
        "product_hard_screener": {"level": "DEBUG"},
        "product_soft_screener": {"level": "DEBUG"},
        "product_synthesizer": {"level": "DEBUG"},
        "product_ingestor": {"level": "DEBUG"},
        "products_screener_pipeline": {"level": "DEBUG"},
        # Common utilities
        "common_llm_utils": {"level": "DEBUG"},
        # External libraries
        "ollama": {"level": "DEBUG"},
        "httpx": {"level": "WARNING"},
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}

# Track if logging has been configured to avoid duplicate configuration
_logging_configured = False


def get_logger(logger_name: str) -> logging.Logger:
    """
    Get a logger instance with the centralized configuration.

    Args:
        logger_name: Name of the logger (e.g., 'product_hard_screener')

    Returns:
        Configured logger instance
    """
    global _logging_configured
    if not _logging_configured:
        logging.config.dictConfig(LOGGING_CONFIG)
        _logging_configured = True
    return logging.getLogger(logger_name)
