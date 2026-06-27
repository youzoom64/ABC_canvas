# powan_id: node-d3b8c6b506
# title: 保持日数クリーンアップ
# parent: node-34e4ee95ea
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable


class LogRetentionCleanupError(ValueError):
    """Raised when retention cleanup settings cannot be used."""


@dataclass(frozen=True)
class CleanupResult:
    """Files selected and deleted by retention cleanup."""

    candidates: tuple[Path, ...]
    deleted: tuple[Path, ...]


def find_expired_log_files(
    directory: str | Path,
    *,
    pattern: str = "*.log*",
    retention_days: int | None = None,
    now: datetime | None = None,
) -> tuple[Path, ...]:
    """Return log files older than retention_days without deleting them."""

    if retention_days is None:
        return ()
    if retention_days < 0:
        raise LogRetentionCleanupError("retention_days must be 0 or greater")

    root = Path(directory)
    if not root.exists():
        return ()
    if not root.is_dir():
        raise LogRetentionCleanupError(f"log cleanup target is not a directory: {root!s}")

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    cutoff = current - timedelta(days=retention_days)

    expired: list[Path] = []
    for path in root.glob(pattern):
        if not path.is_file():
            continue
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if modified < cutoff:
            expired.append(path)
    return tuple(sorted(expired))


def delete_files(paths: Iterable[Path]) -> tuple[Path, ...]:
    """Delete files and return the paths that were actually removed."""

    deleted: list[Path] = []
    for path in paths:
        try:
            path.unlink()
            deleted.append(path)
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise LogRetentionCleanupError(f"failed to delete old log file {path!s}: {exc}") from exc
    return tuple(deleted)


def cleanup_old_log_files(
    directory: str | Path,
    *,
    pattern: str = "*.log*",
    retention_days: int | None = None,
    dry_run: bool = False,
    now: datetime | None = None,
) -> CleanupResult:
    """Find old log files and optionally delete them."""

    candidates = find_expired_log_files(
        directory,
        pattern=pattern,
        retention_days=retention_days,
        now=now,
    )
    deleted = () if dry_run else delete_files(candidates)
    return CleanupResult(candidates=candidates, deleted=deleted)
