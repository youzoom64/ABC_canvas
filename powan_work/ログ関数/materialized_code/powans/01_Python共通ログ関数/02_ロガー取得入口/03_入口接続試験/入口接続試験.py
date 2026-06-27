# powan_id: node-6942ef05b2
# title: 入口接続試験
# parent: node-894cbd722f
# powanKind: organ
# codeLanguage: python

import io
import logging
import uuid


def test_get_logger_connection(get_logger_func):
    """Check the public get_logger(app_name) entrypoint behavior."""
    app_name = f"connection_test_{uuid.uuid4().hex}"

    logger = get_logger_func(app_name)
    assert isinstance(logger, logging.Logger)
    assert logger.name

    original_handlers = tuple(logger.handlers)
    original_handler_ids = {id(handler) for handler in original_handlers}

    stream = io.StringIO()
    probe_handler = logging.StreamHandler(stream)
    probe_handler.setLevel(logging.DEBUG)
    logger.addHandler(probe_handler)
    try:
        marker = f"logger connection marker {uuid.uuid4().hex}"
        logger.info(marker)
        probe_handler.flush()
        assert marker in stream.getvalue()
    finally:
        logger.removeHandler(probe_handler)
        probe_handler.close()

    logger_again = get_logger_func(app_name)
    assert logger_again is logger
    assert isinstance(logger_again, logging.Logger)
    assert tuple(logger_again.handlers) == original_handlers
    assert {id(handler) for handler in logger_again.handlers} == original_handler_ids

    invalid_app_names = ["", "   ", None, 123]
    for invalid_app_name in invalid_app_names:
        try:
            get_logger_func(invalid_app_name)
        except (ValueError, TypeError):
            pass
        else:
            raise AssertionError(
                f"get_logger_func accepted invalid app_name: {invalid_app_name!r}"
            )
