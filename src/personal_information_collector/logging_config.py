import logging
import logging.config

logging_config = {
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
                "level": "INFO",
                "formatter": "rich",
                "show_time": True,
                "show_level": True,
                "show_path": False,
                "markup": True,
            }
        },
        "loggers": {
            "personal_information_collector_core": {"level": "DEBUG"},
            "personal_information_collector_app": {"level": "DEBUG"},
            "ollama": {"level": "DEBUG"},
            "httpx": {"level": "WARNING"}
        },
        "root": {"level": "INFO", "handlers": ["console"]},
    }

def get_logger(logger_name: str):
    """Setup logging configuration for the project"""
    logging.config.dictConfig(logging_config)
    return logging.getLogger(logger_name)
