# powan_id: node-718cee9887
# title: ログレベル判定
# parent: node-5815509426
# powanKind: nerve
# codeLanguage: python

LEVEL_ORDER = ("trace", "debug", "info", "warning", "error", "critical")
LEVEL_STRENGTH = {level: index for index, level in enumerate(LEVEL_ORDER)}


def normalize_log_level(level: str) -> str:
    """Return a canonical six-step log level name."""
    normalized = str(level).strip().lower()
    if normalized not in LEVEL_STRENGTH:
        raise ValueError(f"Unknown log level: {level!r}")
    return normalized


def compare_log_levels(left: str, right: str) -> int:
    """Compare two log levels by strength.

    Returns -1 when left is weaker, 0 when equal, and 1 when left is stronger.
    The ordering is trace < debug < info < warning < error < critical.
    """
    left_strength = LEVEL_STRENGTH[normalize_log_level(left)]
    right_strength = LEVEL_STRENGTH[normalize_log_level(right)]

    if left_strength < right_strength:
        return -1
    if left_strength > right_strength:
        return 1
    return 0


def should_output_for_min_level(target_level: str, minimum_level: str) -> bool:
    """Return True when target_level should be emitted for minimum_level."""
    return compare_log_levels(target_level, minimum_level) >= 0


def judge_log_level(target_level: str, minimum_level: str) -> dict[str, object]:
    """Bundle comparison and minimum-level output judgment for callers."""
    comparison = compare_log_levels(target_level, minimum_level)
    return {
        "targetLevel": normalize_log_level(target_level),
        "minimumLevel": normalize_log_level(minimum_level),
        "comparison": comparison,
        "shouldOutput": comparison >= 0,
    }
