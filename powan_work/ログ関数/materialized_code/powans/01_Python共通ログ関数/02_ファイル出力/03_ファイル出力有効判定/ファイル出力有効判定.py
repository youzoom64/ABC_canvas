# powan_id: node-f6dbb33229
# title: ファイル出力有効判定
# parent: node-92b7df4887
# powanKind: organ
# codeLanguage: python

from typing import Any, Mapping

_TRUE = {"1", "true", "yes", "on", "enable", "enabled"}
_FALSE = {"0", "false", "no", "off", "disable", "disabled"}
_KEYS = ("file_enabled", "enable_file", "log_to_file", "file", "enabled")


def is_file_output_enabled(config: Any = None, default: bool = True) -> bool:
    if config is None:
        return bool(default)
    if isinstance(config, bool):
        return config
    if isinstance(config, str):
        value = config.strip().lower()
        if value in _TRUE:
            return True
        if value in _FALSE:
            return False
        return bool(default)
    if isinstance(config, Mapping):
        for key in _KEYS:
            if key in config:
                return is_file_output_enabled(config[key], default=default)
    if isinstance(config, (int, float)):
        return bool(config)
    return bool(default)
