import logging
import sys
import json
from datetime import datetime
from contextvars import ContextVar

from typing import Optional

# Context var to store request ID
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        }

        # Add Request ID if available
        req_id = request_id_ctx.get()
        if req_id:
            log_obj["request_id"] = req_id

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = JSONFormatter()
    handler.setFormatter(formatter)

    # Remove existing handlers to avoid duplicates
    logger.handlers = []
    logger.addHandler(handler)

    # Silence overly verbose loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    return logging.getLogger(__name__)


logger = setup_logging()
