# powan_id: node-f42fe5d20b
# title: ログレベル比較
# parent: node-718cee9887
# powanKind: organ
# codeLanguage: python

LEVEL_ORDER = ("trace", "debug", "info", "warning", "error", "critical")
LEVEL_STRENGTH = {level: index for index, level in enumerate(LEVEL_ORDER)}


def normalize_log_level(level: str) -> str:
    """Return a canonical log level name, or raise ValueError for unknown levels."""
    normalized = str(level).strip().lower()
    if normalized not in LEVEL_STRENGTH:
        raise ValueError(f"Unknown log level: {level!r}")
    return normalized


def compare_log_levels(left: str, right: str) -> int:
    """Compare two log levels by strength.

    Returns -1 when left is weaker than right, 0 when equal, and 1 when left is stronger.
    The ordering is: trace < debug < info < warning < error < critical.
    """
    left_strength = LEVEL_STRENGTH[normalize_log_level(left)]
    right_strength = LEVEL_STRENGTH[normalize_log_level(right)]

    if left_strength < right_strength:
        return -1
    if left_strength > right_strength:
        return 1
    return 0
