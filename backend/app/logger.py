import logging
import sys


def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers == False:
        logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)

    return logger


logger = setup_logger("firesafety")
