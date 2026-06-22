import sys
from loguru import logger
import os


def setup_logger(log_dir: str = 'logs', level: str = 'INFO'):
    os.makedirs(log_dir, exist_ok=True)
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=level,
        colorize=True
    )
    logger.add(
        os.path.join(log_dir, 'nexuzy_{time:YYYY-MM-DD}.log'),
        rotation='10 MB',
        retention='30 days',
        compression='zip',
        encoding='utf-8',
        level='DEBUG',
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )
    return logger
