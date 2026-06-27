# powan_id: node-1040bed774
# title: ロガー名を整える
# parent: node-894cbd722f
# powanKind: organ
# codeLanguage: python

def normalize_logger_name(app_name: str) -> str:
    """Validate and normalize an app name for ``logging.getLogger``."""
    if app_name is None:
        raise ValueError("app_name is required and cannot be None")

    if not isinstance(app_name, str):
        raise TypeError("app_name must be a string")

    logger_name = app_name.strip()
    if not logger_name:
        raise ValueError("app_name must not be empty or whitespace only")

    return logger_name
