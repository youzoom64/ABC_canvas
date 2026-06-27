# powan_id: node-4ecf8829c2
# title: 最小出力レベル判定
# parent: node-718cee9887
# powanKind: organ
# codeLanguage: python

LOG_LEVEL_ORDER = {
    "trace": 0,
    "debug": 1,
    "info": 2,
    "warning": 3,
    "error": 4,
    "critical": 5,
}


def normalize_log_level(level: str) -> str:
    """Return a canonical log level name or raise ValueError for unknown levels."""
    normalized = str(level).strip().lower()
    if normalized not in LOG_LEVEL_ORDER:
        raise ValueError(f"unknown log level: {level!r}")
    return normalized


def should_output_for_min_level(target_level: str, minimum_level: str) -> bool:
    """Return True when target_level is at least as severe as minimum_level."""
    target = normalize_log_level(target_level)
    minimum = normalize_log_level(minimum_level)
    return LOG_LEVEL_ORDER[target] >= LOG_LEVEL_ORDER[minimum]
