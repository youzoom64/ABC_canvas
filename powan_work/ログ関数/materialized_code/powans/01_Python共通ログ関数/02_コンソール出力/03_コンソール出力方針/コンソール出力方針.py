# powan_id: node-ffda89edb6
# title: コンソール出力方針
# parent: node-30e768b421
# powanKind: nerve
# codeLanguage: python

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, TextIO


@dataclass(frozen=True)
class ConsoleOutputPolicy:
    """Console logging policy assembled from the child powans."""

    enabled: bool
    stream_name: str
    stream: TextIO | None
    is_interactive: bool
    supports_color: bool
    reason: str = ""


EnableResolver = Callable[[Mapping[str, Any] | None, Mapping[str, str] | None], tuple[bool, str]]
StreamResolver = Callable[[str, Mapping[str, Any] | None], tuple[str, TextIO | None]]
TerminalResolver = Callable[[TextIO | None, Mapping[str, str] | None], dict[str, bool]]


def build_console_output_policy(
    *,
    level: str = "INFO",
    config: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
    resolve_enabled: EnableResolver,
    select_stream: StreamResolver,
    inspect_terminal: TerminalResolver,
) -> ConsoleOutputPolicy:
    """Return the policy for whether and where console logs should be emitted.

    The three child powans supply the concrete decisions: enablement, output
    stream selection, and terminal capability inspection.  This nerve powan only
    assembles those answers into one stable interface.
    """

    enabled, reason = resolve_enabled(config, environ)
    stream_name, stream = select_stream(level, config)
    terminal = inspect_terminal(stream, environ)

    return ConsoleOutputPolicy(
        enabled=enabled,
        stream_name=stream_name,
        stream=stream if enabled else None,
        is_interactive=bool(terminal.get("is_interactive", False)) if enabled else False,
        supports_color=bool(terminal.get("supports_color", False)) if enabled else False,
        reason=reason,
    )
