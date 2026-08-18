import logging
from pythonjsonlogger import jsonlogger

def configure_logging(level: str = "INFO"):
    logger = logging.getLogger()
    logger.setLevel(level)

    logHandler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s',
        timestamp=True
    )
    logHandler.setFormatter(formatter)
    
    # Clear existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()
        
    logger.addHandler(logHandler)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
