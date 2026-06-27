# powan_id: node-32182dd2f6
# title: ログ保存先解決
# parent: node-34e4ee95ea
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


class LogPathResolutionError(ValueError):
    """Raised when a log save location cannot be resolved safely."""


@dataclass(frozen=True)
class ResolvedLogPath:
    """Directory, plain filename, and full path ready for logging.FileHandler."""

    directory: Path
    filename: str
    path: Path


_WINDOWS_RESERVED_NAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}
_INVALID_FILENAME_CHARS = re.compile(r"[\x00-\x1f<>:\\|?*/]")


def resolve_log_file_path(
    app_name: str,
    settings: Mapping[str, Any] | None = None,
    *,
    default_dir: str | os.PathLike[str] = "logs",
    create_dir: bool = True,
) -> ResolvedLogPath:
    """Resolve the log directory, filename, and full path.

    The settings mapping may provide ``file_dir`` / ``directory`` / ``dir`` /
    ``log_dir`` and ``file_name`` / ``filename`` / ``name`` / ``log_file``.
    The filename is always treated as a plain filename, never as a path, so it
    can be passed safely to standard logging handlers.
    """

    values = _ensure_mapping(settings)
    directory = _resolve_directory(
        _first_present(values, "file_dir", "directory", "dir", "log_dir", default=default_dir)
    )
    filename = _resolve_filename(
        _first_present(
            values,
            "file_name",
            "filename",
            "name",
            "log_file",
            default=_default_filename(app_name),
        )
    )

    if create_dir:
        _create_directory(directory)

    return ResolvedLogPath(directory=directory, filename=filename, path=directory / filename)


def resolve_log_file_handler_path(
    app_name: str,
    settings: Mapping[str, Any] | None = None,
    *,
    default_dir: str | os.PathLike[str] = "logs",
    create_dir: bool = True,
) -> Path:
    """Return only the path value expected by logging.FileHandler."""

    return resolve_log_file_path(
        app_name,
        settings,
        default_dir=default_dir,
        create_dir=create_dir,
    ).path


def _ensure_mapping(settings: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if settings is None:
        return {}
    if not isinstance(settings, Mapping):
        raise TypeError("log path settings must be a mapping or None")
    return settings


def _first_present(settings: Mapping[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in settings:
            return settings[name]
    return default


def _default_filename(app_name: str) -> str:
    raw_name = str(app_name or "app").strip() or "app"
    filename = "".join("_" if char.isspace() or _INVALID_FILENAME_CHARS.match(char) else char for char in raw_name)
    filename = filename.strip("._ ") or "app"
    return f"{filename}.log"


def _resolve_directory(value: Any) -> Path:
    if isinstance(value, Path):
        directory = value
    elif isinstance(value, os.PathLike):
        directory = Path(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise LogPathResolutionError("log directory must not be empty")
        directory = Path(text)
    else:
        raise LogPathResolutionError(f"log directory must be path-like, got {value!r}")

    try:
        return Path(os.path.expandvars(str(directory))).expanduser()
    except RuntimeError as exc:
        raise LogPathResolutionError(f"failed to expand log directory {directory!s}: {exc}") from exc


def _resolve_filename(value: Any) -> str:
    if isinstance(value, os.PathLike):
        filename = os.fspath(value)
    else:
        filename = str(value or "")

    filename = filename.strip()
    if not filename:
        raise LogPathResolutionError("log filename must not be empty")

    path = Path(filename)
    if path.is_absolute() or len(path.parts) != 1:
        raise LogPathResolutionError("log filename must be a plain filename, not a path")
    if filename in {".", ".."}:
        raise LogPathResolutionError("log filename must name a file, not a directory marker")
    if _INVALID_FILENAME_CHARS.search(filename):
        raise LogPathResolutionError(f"log filename contains unsafe characters: {filename!r}")
    if filename.endswith((" ", ".")):
        raise LogPathResolutionError(f"log filename must not end with a space or dot: {filename!r}")

    stem = filename.split(".", 1)[0].strip().lower()
    if stem in _WINDOWS_RESERVED_NAMES:
        raise LogPathResolutionError(f"log filename uses a reserved Windows device name: {filename!r}")

    return filename


def _create_directory(directory: Path) -> None:
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise LogPathResolutionError(f"failed to create log directory {directory!s}: {exc}") from exc
