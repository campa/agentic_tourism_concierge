import logging
import logging.config


def setup_logging():
    """Setup logging configuration for the project"""

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            }
        },
        "loggers": {
            "agentic_tourism_concierge": {"level": "DEBUG"},
            "ollama": {"level": "DEBUG"}
        },
        "root": {"level": "INFO", "handlers": ["console"]},
    }

    logging.config.dictConfig(logging_config)

    return logging.getLogger("agentic_tourism_concierge")
