import logging
import colorlog

def setup_logger(name: str = "app") -> logging.Logger:
    logger = logging.getLogger(name)
    
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.INFO)

    log_format = (
        "%(log_color)s%(asctime)s - %(levelname)-8s - %(message)s%(reset)s"
    )

    color_formatter = colorlog.ColoredFormatter(
        log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        reset=True,
        log_colors={
            'DEBUG':    'cyan',
            'INFO':     'green',
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'red,bg_white',
        },
        secondary_log_colors={},
        style='%'
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(color_formatter)
    logger.addHandler(console_handler)

    return logger

logger = setup_logger("AI_Job_Recommender")
