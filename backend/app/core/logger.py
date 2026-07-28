import logging
import contextvars

# Context variable to hold request ID
request_id_var = contextvars.ContextVar("request_id", default="-")

class RequestIdFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, "request_id"):
            record.request_id = request_id_var.get()
        return True

# Configure logging with a structured format
log_format = "%(asctime)s [%(levelname)s] [%(name)s] [req_id=%(request_id)s] %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)

for handler in logging.getLogger().handlers:
    handler.addFilter(RequestIdFilter())

logger = logging.getLogger("firesafety_app")
