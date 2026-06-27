# powan_id: node-d20af7cf06
# title: 例外記録オプション
# parent: node-76c5714ad9
# powanKind: nerve
# codeLanguage: python

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from typing import Any, Mapping


@dataclass(frozen=True)
class ExceptionLogOptions:
    """Options that control how exception details are rendered for logs."""

    include_stack: bool = True
    include_chain: bool = True
    include_context: bool = True
    mask_secrets: bool = True
    max_stack_lines: int = 80


def _option_value(options: Any, name: str, default: Any) -> Any:
    if options is None:
        return default
    if isinstance(options, Mapping):
        return options.get(name, default)
    return getattr(options, name, default)


def _coerce_positive_int(value: Any, *, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return number if number > 0 else default


def should_include_stack(options: Any = None, *, default: bool = True) -> bool:
    """Decide whether traceback text should be included."""

    return bool(_option_value(options, "include_stack", default))


def should_include_chain(options: Any = None, *, default: bool = True) -> bool:
    """Decide whether exception cause/context chains should be included."""

    return bool(_option_value(options, "include_chain", default))


def should_include_context(options: Any = None, *, default: bool = True) -> bool:
    """Decide whether caller-supplied context should be included."""

    return bool(_option_value(options, "include_context", default))


def should_mask_secrets(options: Any = None, *, default: bool = True) -> bool:
    """Decide whether sensitive-looking values should be masked."""

    return bool(_option_value(options, "mask_secrets", default))


def normalize_exception_options(options: ExceptionLogOptions | Mapping[str, Any] | Any | None = None) -> ExceptionLogOptions:
    """Normalize mapping or object options into ExceptionLogOptions."""

    defaults = ExceptionLogOptions()
    if options is None:
        return defaults
    if isinstance(options, ExceptionLogOptions):
        return options

    values: dict[str, Any] = {}
    for field in fields(ExceptionLogOptions):
        values[field.name] = _option_value(options, field.name, getattr(defaults, field.name))

    return ExceptionLogOptions(
        include_stack=bool(values["include_stack"]),
        include_chain=bool(values["include_chain"]),
        include_context=bool(values["include_context"]),
        mask_secrets=bool(values["mask_secrets"]),
        max_stack_lines=_coerce_positive_int(values["max_stack_lines"], default=defaults.max_stack_lines),
    )


def merge_exception_options(base: ExceptionLogOptions | Mapping[str, Any] | Any | None = None, **overrides: Any) -> ExceptionLogOptions:
    """Return normalized options with non-None keyword overrides applied."""

    normalized = normalize_exception_options(base)
    allowed = {field.name for field in fields(ExceptionLogOptions)}
    clean_overrides = {key: value for key, value in overrides.items() if key in allowed and value is not None}
    if not clean_overrides:
        return normalized
    return normalize_exception_options(replace(normalized, **clean_overrides))
