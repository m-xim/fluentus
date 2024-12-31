import sys

from loguru import logger

from src.utils.qt_error import excepthook


def configure_logger():
    """Configures the Loguru logger with console and file handlers."""

    logger.remove()

    # Add console handler with colorized output if stderr is a TTY
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "{message}"
    )

    if sys.stderr and not sys.stderr.isatty():
        logger.add(
            sys.stderr,
            format=log_format,
            level="INFO",
            colorize=True,
            enqueue=True
        )

    # Add file handler with rotation, retention, and compression
    logger.add(
        "fluentus.log",
        rotation="10 MB",
        retention="10 days",
        compression="zip",
        format=log_format,
        enqueue=True,
        backtrace=True,  # Provides full stack traces
        diagnose=True,  # Adds variable information to stack traces
    )

    # Define a handler for uncaught exceptions
    def exception_handler(exception_type, exception, traceback):
        logger.opt(exception=True).error(f"An unhandled exception occurred {exception_type}, {exception}, {traceback}")
        excepthook(exception_type, exception, traceback)

    sys.excepthook = exception_handler
