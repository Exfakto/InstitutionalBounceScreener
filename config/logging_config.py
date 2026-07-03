import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


DEFAULT_LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | %(threadName)s | %(message)s"
)


def configure_logging(level="INFO", log_dir="logs", log_file="application.log"):
    numeric_level = getattr(logging, str(level or "INFO").upper(), logging.INFO)
    destination = Path(log_dir)
    destination.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
    root = logging.getLogger()
    root.setLevel(numeric_level)
    root.handlers.clear()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        destination / log_file,
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)

    root.addHandler(console_handler)
    root.addHandler(file_handler)
    return root

logger = logging.getLogger("IBS")


configure_logging()
