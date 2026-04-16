import json
import logging
from datetime import datetime, timezone


NOISY_LOGGERS: dict[str, int] = {
    "httpx": logging.WARNING,
    "httpcore": logging.WARNING,
    "LiteLLM": logging.WARNING,
    "litellm": logging.WARNING,
    "crewai.cli.config": logging.WARNING,
    "watchfiles.main": logging.WARNING,
}


class JsonFormatter(logging.Formatter):
    """Minimal JSON formatter for structured application logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging once for the application."""

    root_logger = logging.getLogger()
    if root_logger.handlers:
        root_logger.setLevel(level.upper())
        for logger_name, logger_level in NOISY_LOGGERS.items():
            logging.getLogger(logger_name).setLevel(logger_level)
        return

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root_logger.addHandler(handler)
    root_logger.setLevel(level.upper())
    for logger_name, logger_level in NOISY_LOGGERS.items():
        logging.getLogger(logger_name).setLevel(logger_level)
