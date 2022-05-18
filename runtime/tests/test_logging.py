from anyforce import logging


def test_logging():
    logger = logging.getLogger("test")
    logger.with_field(k="v").debug("debug")
    logger.with_field(k="v").info("info")
    logger.with_field(k="v").warning("warning")
    logger.with_field(k="v").success("success")
    logger.with_field(k="v").log(logging.INFO, "info")
