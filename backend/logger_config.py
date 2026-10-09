import logging
import sys
from copy import copy
from uvicorn.logging import DefaultFormatter


class ColoredFormatter(DefaultFormatter):
    """
    Uvicorn-compatible colored log formatter.
    Formats levels as:
      INFO:     (blue/green)
      WARN:     (yellow)
      ERROR:    (red)
    """

    def formatMessage(self, record: logging.LogRecord) -> str:
        recordcopy = copy(record)
        levelname = "WARN" if recordcopy.levelno == logging.WARNING else recordcopy.levelname
        separator = " " * (8 - len(levelname))
        if self.use_colors:
            levelname = self.color_level_name(levelname, recordcopy.levelno)
            if "color_message" in recordcopy.__dict__:
                recordcopy.msg = recordcopy.__dict__["color_message"]
                recordcopy.__dict__["message"] = recordcopy.getMessage()
        recordcopy.__dict__["levelprefix"] = levelname + ":" + separator
        return logging.Formatter.formatMessage(self, recordcopy)


def setup_logging():
    """Configure root and uvicorn loggers with colored WARN and ERROR prefixes."""
    handler = logging.StreamHandler(sys.stderr)
    formatter = ColoredFormatter("%(levelprefix)s %(message)s", use_colors=True)
    handler.setFormatter(formatter)

    # Configure root logger for all app modules
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = [handler]

    # Also update uvicorn loggers so they share the exact format
    for logger_name in ("uvicorn", "uvicorn.error"):
        u_logger = logging.getLogger(logger_name)
        u_logger.handlers = [handler]
        u_logger.propagate = False
