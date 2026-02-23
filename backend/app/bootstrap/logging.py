import logging
import sys
from pythonjsonlogger import jsonlogger
from app.core.config import settings

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        if not log_record.get('timestamp'):
            # this doesn't use record.created, so it is slightly off
            from datetime import datetime
            log_record['timestamp'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname

def setup_logging():
    log_handler = logging.StreamHandler(sys.stdout)
    formatter = CustomJsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s')
    log_handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(log_handler)
    root_logger.setLevel(logging.INFO)

    # Uvicorn loggers
    logging.getLogger("uvicorn.access").handlers = [log_handler]
    logging.getLogger("uvicorn.error").handlers = [log_handler]
    
    # SQLAlchemy (Set to INFO/WARN in prod)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    logging.info("JSON Logging setup complete.")
