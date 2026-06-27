# powan_id: node-cf105c59bb
# title: タイムゾーン扱い
# parent: node-501b2212e6
# powanKind: organ
# codeLanguage: python

from __future__ import annotations

from datetime import datetime, timezone, tzinfo


def apply_timezone(moment: datetime, tz: tzinfo | None = None) -> datetime:
    target = tz or timezone.utc
    if moment.tzinfo is None:
        return moment.replace(tzinfo=target)
    return moment.astimezone(target)
