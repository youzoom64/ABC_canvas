# powan_id: node-34e4ee95ea
# title: ファイル出力設定
# parent: node-a3e5f7eb89
# powanKind: nerve
# codeLanguage: python

from __future__ import annotations

from dataclasses import dataclass
import logging
from logging import Handler
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Mapping
from datetime import datetime, timedelta, timezone


class FileLogConfigError(ValueError):
    """Raised when file logging configuration cannot be used safely."""


@dataclass(frozen=True)
class RotationPolicy:
    """Rotation options for file logging."""

    mode: str = "none"
    max_bytes: int = 0
    backup_count: int = 7
    when: str = "midnight"
    interval: int = 1
    utc: bool = False


@dataclass(frozen=True)
class FileOutputConfig:
    """Resolved file logging settings ready for standard logging."""

    enabled: bool
    directory: Path
    filename: str
    path: Path
    rotation: RotationPolicy
    encoding: str = "utf-8"
    delay: bool = True
    retention_days: int | None = None
    cleanup_pattern: str = "*.log*"


@dataclass(frozen=True)
class CleanupResult:
    """Old log files selected and removed by retention cleanup."""

    candidates: tuple[Path, ...]
    deleted: tuple[Path, ...]


def _setting(settings: Mapping[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in settings:
            return settings[name]
    return default


def _as_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on", "enable", "enabled"}:
            return True
        if normalized in {"0", "false", "no", "n", "off", "disable", "disabled"}:
            return False
        if normalized == "":
            return default
    raise FileLogConfigError(f"file logging boolean setting is invalid: {value!r}")


def file_output_enabled(settings: Mapping[str, Any] | None, *, default: bool = False) -> bool:
    """Return whether file logging should be enabled."""

    settings = settings or {}
    value = _setting(settings, "file_enabled", "file", "enabled", "use_file", default=None)
    return _as_bool(value, default=default)


def generate_log_filename(app_name: str, settings: Mapping[str, Any] | None = None) -> str:
    """Generate or validate a plain filename for a log file."""

    settings = settings or {}
    explicit = _setting(settings, "file_name", "filename", "name", "log_file", default=None)
    if explicit:
        filename = str(explicit).strip()
    else:
        blocked = {"/", "\\", ":", "*", "?", '"', "<", ">", "|"}
        stem_source = _setting(settings, "file_stem", default=app_name) or "app"
        stem = "".join("_" if char in blocked or char.isspace() else char for char in str(stem_source).strip())
        stem = stem.strip("._") or "app"
        suffix_format = _setting(settings, "date_suffix", "filename_date_format", default="")
        suffix = datetime.now().strftime(str(suffix_format)) if suffix_format else ""
        extension = str(_setting(settings, "extension", default=".log") or "")
        if extension and not extension.startswith("."):
            extension = "." + extension
        filename = f"{stem}{('-' + suffix) if suffix else ''}{extension}"

    candidate = Path(filename)
    if not filename or candidate.is_absolute() or candidate.parent != Path("."):
        raise FileLogConfigError("log filename must be a plain filename")
    if filename in {".", ".."}:
        raise FileLogConfigError("log filename must name a file")
    return filename


def resolve_log_file_path(
    app_name: str,
    settings: Mapping[str, Any] | None = None,
    *,
    default_dir: str | Path = "logs",
    create_dir: bool = True,
) -> tuple[Path, str, Path]:
    """Resolve directory, filename, and full path for file logging."""

    settings = settings or {}
    directory_value = _setting(settings, "file_dir", "directory", "dir", "log_dir", default=default_dir)
    try:
        directory = Path(directory_value).expanduser()
    except TypeError as exc:
        raise FileLogConfigError("log directory must be a path-like value") from exc

    filename = generate_log_filename(app_name, settings)
    if create_dir:
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise FileLogConfigError(f"failed to create log directory {directory!s}: {exc}") from exc
    return directory, filename, directory / filename


def parse_rotation_policy(settings: Mapping[str, Any] | None = None) -> RotationPolicy:
    """Normalize rotation settings for logging handlers."""

    settings = settings or {}
    raw_mode = _setting(settings, "rotation", "rotation_mode", default="none")
    if raw_mode is True:
        raw_mode = "size"
    if raw_mode is False or raw_mode is None:
        raw_mode = "none"
    mode = str(raw_mode).strip().lower()
    mode = {"off": "none", "bytes": "size", "daily": "time", "date": "time"}.get(mode, mode)
    if mode not in {"none", "size", "time"}:
        raise FileLogConfigError(f"unknown file logging rotation mode: {mode!r}")

    max_bytes = int(_setting(settings, "max_bytes", "rotation_max_bytes", default=0) or 0)
    backup_count = int(_setting(settings, "backup_count", "retention_count", "keep_files", default=7) or 0)
    when = str(_setting(settings, "when", "rotation_when", default="midnight") or "midnight")
    interval = int(_setting(settings, "interval", "rotation_interval", default=1) or 1)
    utc = _as_bool(_setting(settings, "utc", "rotation_utc", default=None), default=False)

    if mode == "size" and max_bytes <= 0:
        raise FileLogConfigError("size rotation requires max_bytes greater than 0")
    if backup_count < 0:
        raise FileLogConfigError("backup_count must be 0 or greater")
    if interval <= 0:
        raise FileLogConfigError("rotation interval must be greater than 0")
    return RotationPolicy(mode=mode, max_bytes=max_bytes, backup_count=backup_count, when=when, interval=interval, utc=utc)


def resolve_file_output_config(
    app_name: str,
    settings: Mapping[str, Any] | None = None,
    *,
    default_enabled: bool = False,
    default_dir: str | Path = "logs",
    create_dir: bool = True,
) -> FileOutputConfig:
    """Resolve dict-like settings into a reusable file-output config."""

    settings = settings or {}
    enabled = file_output_enabled(settings, default=default_enabled)
    directory, filename, path = resolve_log_file_path(app_name, settings, default_dir=default_dir, create_dir=create_dir)
    retention_value = _setting(settings, "retention_days", "keep_days", default=None)
    retention_days = None if retention_value is None else int(retention_value)
    if retention_days is not None and retention_days < 0:
        raise FileLogConfigError("retention_days must be 0 or greater")
    return FileOutputConfig(
        enabled=enabled,
        directory=directory,
        filename=filename,
        path=path,
        rotation=parse_rotation_policy(settings),
        encoding=str(_setting(settings, "encoding", "file_encoding", default="utf-8") or "utf-8"),
        delay=_as_bool(_setting(settings, "delay", "file_delay", default=None), default=True),
        retention_days=retention_days,
        cleanup_pattern=str(_setting(settings, "cleanup_pattern", default="*.log*") or "*.log*"),
    )


def create_file_handler(
    config: FileOutputConfig,
    *,
    level: int | str = logging.INFO,
    formatter: logging.Formatter | None = None,
) -> Handler | None:
    """Create a standard logging file handler, or None when disabled."""

    if not config.enabled:
        return None
    policy = config.rotation
    try:
        if policy.mode == "size":
            handler: Handler = RotatingFileHandler(
                config.path,
                maxBytes=policy.max_bytes,
                backupCount=policy.backup_count,
                encoding=config.encoding,
                delay=config.delay,
            )
        elif policy.mode == "time":
            handler = TimedRotatingFileHandler(
                config.path,
                when=policy.when,
                interval=policy.interval,
                backupCount=policy.backup_count,
                encoding=config.encoding,
                delay=config.delay,
                utc=policy.utc,
            )
        else:
            handler = logging.FileHandler(config.path, encoding=config.encoding, delay=config.delay)
    except OSError as exc:
        raise FileLogConfigError(f"failed to open log file {config.path!s}: {exc}") from exc

    handler.setLevel(level)
    if formatter is not None:
        handler.setFormatter(formatter)
    return handler


def cleanup_old_log_files(config: FileOutputConfig, *, dry_run: bool = False) -> CleanupResult:
    """Clean old log files using the resolved retention settings."""

    if config.retention_days is None:
        return CleanupResult(candidates=(), deleted=())
    if not config.directory.exists():
        return CleanupResult(candidates=(), deleted=())

    cutoff = datetime.now(timezone.utc) - timedelta(days=config.retention_days)
    candidates = tuple(
        sorted(
            path
            for path in config.directory.glob(config.cleanup_pattern)
            if path.is_file() and datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc) < cutoff
        )
    )
    deleted: list[Path] = []
    if not dry_run:
        for path in candidates:
            try:
                path.unlink()
                deleted.append(path)
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise FileLogConfigError(f"failed to delete old log file {path!s}: {exc}") from exc
    return CleanupResult(candidates=candidates, deleted=tuple(deleted))


def build_file_output_handler(
    app_name: str,
    settings: Mapping[str, Any] | None = None,
    *,
    level: int | str = logging.INFO,
    formatter: logging.Formatter | None = None,
    default_enabled: bool = False,
    default_dir: str | Path = "logs",
    cleanup: bool = True,
) -> Handler | None:
    """Resolve settings, optionally cleanup old files, and return a logging handler."""

    config = resolve_file_output_config(
        app_name,
        settings,
        default_enabled=default_enabled,
        default_dir=default_dir,
    )
    if cleanup:
        cleanup_old_log_files(config)
    return create_file_handler(config, level=level, formatter=formatter)
