# powan_id: node-90c2d94129
# title: アプリ識別表示
# parent: node-c6a89ade0d
# powanKind: nerve
# codeLanguage: python

from __future__ import annotations

from dataclasses import dataclass


DEFAULT_APP_LABEL = "app"
DEFAULT_ROOT_LOGGER_LABEL = "root"


def _clean_label(value: object | None) -> str:
    """Return a single-line display label with surrounding whitespace removed."""
    text = str(value or "").strip()
    return " ".join(text.split())


def display_app_name(app_name: object | None, fallback: str = DEFAULT_APP_LABEL) -> str:
    """Format an explicit application name for a log line."""
    return _clean_label(app_name) or fallback


def display_logger_name(logger_name: object | None, max_parts: int | None = None) -> str:
    """Format a standard logging logger name into a compact human label."""
    name = _clean_label(logger_name)
    if not name:
        return DEFAULT_ROOT_LOGGER_LABEL

    parts = [part for part in name.split(".") if part]
    if max_parts is not None and max_parts > 0:
        parts = parts[-max_parts:]
    return ".".join(parts) or DEFAULT_ROOT_LOGGER_LABEL


def fallback_app_name(
    app_name: object | None,
    logger_name: object | None,
    default: str = DEFAULT_APP_LABEL,
) -> str:
    """Resolve a missing app name from the logger namespace or a default label."""
    explicit = _clean_label(app_name)
    if explicit:
        return explicit

    logger_label = display_logger_name(logger_name)
    if logger_label != DEFAULT_ROOT_LOGGER_LABEL:
        return logger_label.split(".", 1)[0] or default
    return default


@dataclass(frozen=True)
class AppIdentityDisplay:
    """Bundle the app identity shown by a shared log formatter."""

    app_name: str
    logger_name: str

    @classmethod
    def from_values(
        cls,
        app_name: object | None = None,
        logger_name: object | None = None,
        *,
        default_app: str = DEFAULT_APP_LABEL,
        logger_max_parts: int | None = None,
    ) -> "AppIdentityDisplay":
        resolved_app = fallback_app_name(app_name, logger_name, default_app)
        resolved_logger = display_logger_name(logger_name, logger_max_parts)
        return cls(app_name=display_app_name(resolved_app, default_app), logger_name=resolved_logger)

    def bracket_label(self) -> str:
        """Return a stable compact label such as 'myapp:service.worker'."""
        if self.logger_name == DEFAULT_ROOT_LOGGER_LABEL or self.logger_name == self.app_name:
            return self.app_name
        return f"{self.app_name}:{self.logger_name}"


def resolve_app_identity(
    app_name: object | None = None,
    logger_name: object | None = None,
    *,
    default_app: str = DEFAULT_APP_LABEL,
    logger_max_parts: int | None = None,
) -> AppIdentityDisplay:
    """Create the shared app/logger identity used by the log output formatter."""
    return AppIdentityDisplay.from_values(
        app_name,
        logger_name,
        default_app=default_app,
        logger_max_parts=logger_max_parts,
    )
