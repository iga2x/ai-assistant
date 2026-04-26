import logging
from rich.logging import RichHandler
from assistant.utils.paths import get_log_file, ensure_dirs

def setup_logger(level=logging.INFO):
    """Setup logging to console and file."""
    ensure_dirs()
    log_file = get_log_file()

    # Create logger
    logger = logging.getLogger("assistant")
    logger.setLevel(level)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # Console handler using Rich
    console_handler = RichHandler(rich_tracebacks=True, markup=True)
    console_handler.setLevel(level)
    console_format = logging.Formatter("%(message)s", datefmt="[%X]")
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)  # Always log debug to file
    file_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)

    return logger

logger = logging.getLogger("assistant")
