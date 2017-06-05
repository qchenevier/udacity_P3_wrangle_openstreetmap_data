import logging

from sys import platform

logging.basicConfig(level=logging.DEBUG)
if platform != "win32":
    try:
        import colorlog
        handler = colorlog.StreamHandler()
        handler.setFormatter(
            colorlog.ColoredFormatter('%(log_color)s%(levelname)s:%(name)s:%(message)s'))
        logger = colorlog.getLogger()
        logger.handlers = [handler]
        logging.debug('colorlog imported')
    except Exception as e:
        logging.debug('colorlog not imported')
        logging.debug(e)
