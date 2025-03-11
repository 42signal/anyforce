from anyforce import logging


def test_logging():
    logger = logging.get_logger("test")
    logger.bind(k="v").debug("debug")
    logger.bind(k="v").info("info")
    logger.bind(k="v").warning("warning")
    logger.bind(k="v").log(logging.INFO, "info")
