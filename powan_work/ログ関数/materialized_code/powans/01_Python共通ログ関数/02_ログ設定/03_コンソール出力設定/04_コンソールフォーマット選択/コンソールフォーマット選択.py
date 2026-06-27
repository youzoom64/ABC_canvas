# powan_id: node-7079986651
# title: コンソールフォーマット選択
# parent: node-ef620afdd3
# powanKind: organ
# codeLanguage: python

"""Console format selection helpers.

This organ powan chooses how console log records are displayed. It accepts a
preset name, a custom standard-library logging format string, or a mapping that
contains format options, then returns a small dataclass that is easy for a
console handler builder to pass into ``logging.Formatter``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from typing import Any, Mapping


DEFAULT_CONSOLE_FORMAT = "standard"
DEFAULT_CONSOLE_DATEFMT = "%Y-%m-%d %H:%M:%S"

_LOG_RECORD_SAMPLE = logging.LogRecord(
    name="sample.app",
    level=logging.INFO,
    pathname="console_format_selection.py",
    lineno=42,
    msg="message",
    args=(),
    exc_info=None,
)

_PRESET_ALIASES: dict[str, str] = {
    "default": "standard",
    "std": "standard",
    "normal": "standard",
    "simple": "plain",
    "message": "plain",
    "msg": "plain",
    "short": "compact",
    "dev": "development",
    "debug": "development",
    "verbose": "detail",
    "full": "detail",
    "json_line": "jsonish",
    "jsonl": "jsonish",
}

_PRESETS: dict[str, str] = {
    "plain": "%(message)s",
    "compact": "%(levelname)s:%(name)s:%(message)s",
    "standard": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
    "development": "%(asctime)s %(levelname)-8s [%(name)s] %(filename)s:%(lineno)d %(message)s",
    "detail": "%(asctime)s %(levelname)s [%(name)s] %(module)s.%(funcName)s:%(lineno)d %(message)s",
    "jsonish": '{"time":"%(asctime)s","level":"%(levelname)s","app":"%(name)s","message":"%(message)s"}',
}

_TIMELESS_PRESETS = {"plain", "compact"}

_FORMAT_STYLE_HINTS = {"%", "{", "$"}


class ConsoleFormatSelectionError(ValueError):
    """Raised when a console logging format cannot be selected or validated."""


@dataclass(frozen=True)
class ConsoleFormatSelection:
    """Resolved console formatter settings.

    Attributes:
        name: Preset name, or ``custom`` for caller-supplied format text.
        format_text: Format string accepted by ``logging.Formatter``.
        datefmt: Optional date format used by ``logging.Formatter``.
        style: Logging formatter style: ``%``, ``{``, or ``$``.
        source: Whether the value came from a preset, custom string, mapping, or
            fallback default.
        includes_time: True when the format displays ``asctime``.
        includes_level: True when the format displays ``levelname``.
        includes_app_name: True when the format displays ``name``.
        includes_message: True when the format displays the log message.
    """

    name: str
    format_text: str
    datefmt: str | None = DEFAULT_CONSOLE_DATEFMT
    style: str = "%"
    source: str = "preset"
    includes_time: bool = False
    includes_level: bool = False
    includes_app_name: bool = False
    includes_message: bool = True

    def make_formatter(self) -> logging.Formatter:
        """Return a ready-to-use standard ``logging.Formatter``."""

        return logging.Formatter(self.format_text, datefmt=self.datefmt, style=self.style)

    def as_dict(self) -> dict[str, Any]:
        """Return a config-friendly representation for parent powans."""

        return {
            "name": self.name,
            "format_text": self.format_text,
            "datefmt": self.datefmt,
            "style": self.style,
            "source": self.source,
            "includes_time": self.includes_time,
            "includes_level": self.includes_level,
            "includes_app_name": self.includes_app_name,
            "includes_message": self.includes_message,
        }

    def without_datefmt(self) -> "ConsoleFormatSelection":
        """Return a copy that lets logging use its own default date style."""

        return replace(self, datefmt=None)


def available_console_format_presets() -> tuple[str, ...]:
    """Return the supported preset names in stable display order."""

    return tuple(_PRESETS.keys())


def select_console_format(
    format_value: str | Mapping[str, Any] | ConsoleFormatSelection | None = None,
    *,
    default: str = DEFAULT_CONSOLE_FORMAT,
    datefmt: str | None = DEFAULT_CONSOLE_DATEFMT,
    style: str | None = None,
) -> ConsoleFormatSelection:
    """Resolve console format input into ``ConsoleFormatSelection``.

    ``format_value`` may be one of these values:

    - ``None`` or an empty string: use ``default``.
    - Preset name such as ``plain``, ``compact``, ``standard``, ``development``,
      ``detail``, or ``jsonish``.
    - Custom logging format string such as ``'%(levelname)s %(message)s'``.
    - Mapping with keys like ``name``, ``format``, ``format_text``, ``datefmt``,
      and ``style``.
    - Existing ``ConsoleFormatSelection`` instance.
    """

    if isinstance(format_value, ConsoleFormatSelection):
        return normalize_existing_selection(format_value, datefmt=datefmt, style=style)

    source = "preset"
    requested_datefmt = datefmt
    requested_style = style

    if isinstance(format_value, Mapping):
        return select_console_format_from_mapping(
            format_value,
            default=default,
            datefmt=requested_datefmt,
            style=requested_style,
        )

    clean = clean_format_value(format_value)
    if clean is None:
        clean = default
        source = "default"

    preset_name = normalize_preset_name(clean)
    if preset_name is not None:
        format_text = _PRESETS[preset_name]
        selection_datefmt = None if preset_name in _TIMELESS_PRESETS else requested_datefmt
        return build_console_format_selection(
            name=preset_name,
            format_text=format_text,
            datefmt=selection_datefmt,
            style=requested_style or "%",
            source=source,
        )

    inferred_style = requested_style or infer_logging_style(clean)
    return build_console_format_selection(
        name="custom",
        format_text=clean,
        datefmt=requested_datefmt,
        style=inferred_style,
        source="custom",
    )


def select_console_format_string(
    format_value: str | Mapping[str, Any] | ConsoleFormatSelection | None = None,
    *,
    default: str = DEFAULT_CONSOLE_FORMAT,
    datefmt: str | None = DEFAULT_CONSOLE_DATEFMT,
    style: str | None = None,
) -> str:
    """Return only the formatter text for callers that want a simple boundary."""

    return select_console_format(format_value, default=default, datefmt=datefmt, style=style).format_text


def create_console_formatter(
    format_value: str | Mapping[str, Any] | ConsoleFormatSelection | None = None,
    *,
    default: str = DEFAULT_CONSOLE_FORMAT,
    datefmt: str | None = DEFAULT_CONSOLE_DATEFMT,
    style: str | None = None,
) -> logging.Formatter:
    """Build a ``logging.Formatter`` directly from console format input."""

    return select_console_format(format_value, default=default, datefmt=datefmt, style=style).make_formatter()


def select_console_format_from_mapping(
    settings: Mapping[str, Any],
    *,
    default: str = DEFAULT_CONSOLE_FORMAT,
    datefmt: str | None = DEFAULT_CONSOLE_DATEFMT,
    style: str | None = None,
) -> ConsoleFormatSelection:
    """Resolve common dict-style settings into a console format selection."""

    mapping_datefmt = first_present(settings, "console_datefmt", "consoleDatefmt", "datefmt", default=datefmt)
    mapping_style = first_present(settings, "console_format_style", "consoleFormatStyle", "format_style", "style", default=style)
    explicit_text = first_present(
        settings,
        "console_format_text",
        "consoleFormatText",
        "format_text",
        "format",
        "text",
        default=None,
    )
    explicit_name = first_present(
        settings,
        "console_format",
        "consoleFormat",
        "format_name",
        "formatName",
        "name",
        default=None,
    )

    if explicit_text is not None and clean_format_value(explicit_text) is not None:
        clean_text = clean_format_value(explicit_text)
        assert clean_text is not None
        return build_console_format_selection(
            name="custom",
            format_text=clean_text,
            datefmt=normalize_optional_string(mapping_datefmt),
            style=normalize_logging_style(mapping_style) if mapping_style is not None else infer_logging_style(clean_text),
            source="mapping",
        )

    return select_console_format(
        explicit_name,
        default=default,
        datefmt=normalize_optional_string(mapping_datefmt),
        style=normalize_logging_style(mapping_style) if mapping_style is not None else None,
    )


def normalize_existing_selection(
    selection: ConsoleFormatSelection,
    *,
    datefmt: str | None,
    style: str | None,
) -> ConsoleFormatSelection:
    """Validate and optionally override an existing selection object."""

    selected_style = normalize_logging_style(style) if style is not None else selection.style
    validate_console_format_text(selection.format_text, style=selected_style)
    selected_datefmt = selection.datefmt if datefmt == DEFAULT_CONSOLE_DATEFMT else datefmt
    return replace(
        selection,
        style=selected_style,
        datefmt=selected_datefmt,
        includes_time=contains_field(selection.format_text, "asctime", selected_style),
        includes_level=contains_field(selection.format_text, "levelname", selected_style),
        includes_app_name=contains_field(selection.format_text, "name", selected_style),
        includes_message=contains_message_field(selection.format_text, selected_style),
    )


def build_console_format_selection(
    *,
    name: str,
    format_text: str,
    datefmt: str | None,
    style: str,
    source: str,
) -> ConsoleFormatSelection:
    """Validate values and return a populated selection dataclass."""

    normalized_style = normalize_logging_style(style)
    clean_text = validate_console_format_text(format_text, style=normalized_style)
    clean_datefmt = normalize_optional_string(datefmt)
    return ConsoleFormatSelection(
        name=name,
        format_text=clean_text,
        datefmt=clean_datefmt,
        style=normalized_style,
        source=source,
        includes_time=contains_field(clean_text, "asctime", normalized_style),
        includes_level=contains_field(clean_text, "levelname", normalized_style),
        includes_app_name=contains_field(clean_text, "name", normalized_style),
        includes_message=contains_message_field(clean_text, normalized_style),
    )


def validate_console_format_text(format_text: str, *, style: str = "%") -> str:
    """Return clean formatter text or raise a helpful error."""

    clean = str(format_text).strip()
    if not clean:
        raise ConsoleFormatSelectionError("Console format text cannot be empty.")
    normalized_style = normalize_logging_style(style)
    if not looks_like_logging_format(clean, normalized_style):
        raise ConsoleFormatSelectionError(
            f"Console format {format_text!r} does not look like a logging format for style {normalized_style!r}."
        )
    try:
        logging.Formatter(clean, style=normalized_style).format(_LOG_RECORD_SAMPLE)
    except Exception as exc:
        raise ConsoleFormatSelectionError(f"Invalid console logging format {format_text!r}: {exc}") from exc
    return clean


def clean_format_value(value: Any) -> str | None:
    """Normalize raw user input while treating blank values as unspecified."""

    if value is None:
        return None
    clean = str(value).strip()
    return clean or None


def normalize_preset_name(value: str) -> str | None:
    """Return a supported preset name, resolving aliases, or ``None``."""

    key = value.strip().lower().replace("-", "_").replace(" ", "_")
    key = _PRESET_ALIASES.get(key, key)
    if key in _PRESETS:
        return key
    return None


def normalize_logging_style(value: Any) -> str:
    """Normalize and validate the style argument for ``logging.Formatter``."""

    clean = str(value or "%").strip()
    if clean not in _FORMAT_STYLE_HINTS:
        raise ConsoleFormatSelectionError("Console format style must be one of '%', '{', or '$'.")
    return clean


def infer_logging_style(format_text: str) -> str:
    """Infer logging format style from placeholders in custom text."""

    if "%(" in format_text:
        return "%"
    if "{" in format_text and "}" in format_text:
        return "{"
    if "$" in format_text:
        return "$"
    raise ConsoleFormatSelectionError(
        "Custom console format must contain logging placeholders such as '%(message)s', '{message}', or '$message'."
    )


def looks_like_logging_format(format_text: str, style: str) -> bool:
    """Return whether text contains at least one placeholder for the style."""

    if style == "%":
        return "%(" in format_text
    if style == "{":
        return "{" in format_text and "}" in format_text
    if style == "$":
        return "$" in format_text
    return False


def contains_field(format_text: str, field_name: str, style: str) -> bool:
    """Return whether the format text references a log record field."""

    if style == "%":
        return f"%({field_name})" in format_text
    if style == "{":
        return "{" + field_name in format_text
    if style == "$":
        return f"${field_name}" in format_text or "${" + field_name + "}" in format_text
    return False


def contains_message_field(format_text: str, style: str) -> bool:
    """Return whether the selected format includes the rendered message."""

    return contains_field(format_text, "message", style) or contains_field(format_text, "msg", style)


def normalize_optional_string(value: Any) -> str | None:
    """Return stripped string values while preserving ``None`` and blanks as None."""

    if value is None:
        return None
    clean = str(value).strip()
    return clean or None


def first_present(source: Mapping[str, Any], *keys: str, default: Any) -> Any:
    """Return the first key that exists in ``source`` even when the value is falsy."""

    for key in keys:
        if key in source:
            return source[key]
    return default


__all__ = [
    "ConsoleFormatSelection",
    "ConsoleFormatSelectionError",
    "DEFAULT_CONSOLE_DATEFMT",
    "DEFAULT_CONSOLE_FORMAT",
    "available_console_format_presets",
    "create_console_formatter",
    "select_console_format",
    "select_console_format_from_mapping",
    "select_console_format_string",
    "validate_console_format_text",
]
