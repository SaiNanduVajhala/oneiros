"""
Oneiros Utilities - Logger Configuration

Bootstraps logging formatting and levels across Oneiros kernel packages.
"""

import logging
import sys

def setup_logger(name: str = "oneiros", level: int = logging.INFO) -> logging.Logger:
    """
    Configures and returns a stderr logging instance.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    return logger
