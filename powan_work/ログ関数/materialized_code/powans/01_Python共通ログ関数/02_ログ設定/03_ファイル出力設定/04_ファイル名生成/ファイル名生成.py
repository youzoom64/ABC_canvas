# powan_id: node-97b1489b9e
# title: ファイル名生成
# parent: node-34e4ee95ea
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping


class LogFilenameError(ValueError):
    """Raised when a log filename cannot be generated safely."""


_BLOCKED = {"/", "\\", ":", "*", "?", '"', "<", ">", "|"}


def safe_name_part(value: Any, *, fallback: str = "app") -> str:
    """Return a filesystem-safe filename part without path separators."""

    text = str(value or "").strip() or fallback
    safe = "".join("_" if char in _BLOCKED or char.isspace() else char for char in text)
    safe = safe.strip("._") or fallback
    return safe


def generate_log_filename(
    app_name: str,
    settings: Mapping[str, Any] | None = None,
    *,
    default_extension: str = ".log",
    now: datetime | date | None = None,
) -> str:
    """Generate a plain log filename from app/config values."""

    settings = settings or {}
    explicit = settings.get("file_name") or settings.get("filename") or settings.get("log_file")
    if explicit:
        filename = str(explicit).strip()
    else:
        stem = safe_name_part(settings.get("file_stem") or app_name)
        suffix_format = settings.get("date_suffix") or settings.get("filename_date_format")
        suffix = ""
        if suffix_format:
            current = now or datetime.now()
            suffix = "-" + current.strftime(str(suffix_format))
        extension = str(settings.get("extension") or default_extension or "")
        if extension and not extension.startswith("."):
            extension = "." + extension
        filename = f"{stem}{suffix}{extension}"

    path = Path(filename)
    if not filename or path.is_absolute() or path.parent != Path("."):
        raise LogFilenameError("log filename must be a plain filename")
    if filename in {".", ".."}:
        raise LogFilenameError("log filename must name a file")
    return filename
