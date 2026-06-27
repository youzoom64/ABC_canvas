# powan_id: node-6aaf570c9f
# title: TRACEレベル登録
# parent: node-5411088125
# powanKind: organ
# codeLanguage: python

"""Idempotent TRACE level registration for Python logging.

This organ powan owns the small but important bridge between the standard
:mod:`logging` module and a custom TRACE level.  It registers level value ``5``
under the name ``TRACE`` and installs ``logging.Logger.trace`` so applications
can write ``logger.trace(...)`` with the same calling style as ``debug`` or
``info``.

The public functions are deliberately narrow:

* ``register_trace_level`` performs the mutation once and returns a registration
  report that later powans can inspect.
* ``ensure_trace_logger`` validates a logger-like object and optionally applies
  TRACE as its level.
* ``is_trace_registered`` and ``get_trace_registration`` provide lightweight
  diagnostics for startup checks and tests.

All mutation is protected by a lock so repeated imports, repeated setup calls,
or parallel application initialization do not create conflicting methods.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from threading import RLock
from types import MethodType
from typing import Any, Final, Protocol, TypeGuard, cast

TRACE_LEVEL: Final[int] = 5
TRACE_NAME: Final[str] = "TRACE"
_TRACE_METHOD_NAME: Final[str] = "trace"


class TraceRegistrationError(RuntimeError):
    """Raised when TRACE cannot be safely connected to ``logging``."""


class TraceLoggerProtocol(Protocol):
    """Protocol for objects that expose the installed ``trace`` method."""

    def trace(
        self,
        msg: object,
        *args: object,
        exc_info: Any = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Log ``msg`` at the TRACE level."""


@dataclass(frozen=True, slots=True)
class TraceRegistration:
    """Result of connecting the custom TRACE level to ``logging``.

    ``level_added`` records whether this call changed the level-name mapping.
    ``method_added`` records whether this call installed ``Logger.trace``.
    ``already_registered`` is true when no mutation was required in this call.
    """

    level: int
    name: str
    level_added: bool
    method_added: bool
    already_registered: bool

    @property
    def method_name(self) -> str:
        """Return the installed logger method name."""

        return _TRACE_METHOD_NAME

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-friendly registration summary."""

        return {
            "level": self.level,
            "name": self.name,
            "methodName": self.method_name,
            "levelAdded": self.level_added,
            "methodAdded": self.method_added,
            "alreadyRegistered": self.already_registered,
        }


_TRACE_LOCK = RLock()
_TRACE_REGISTERED = False
_LAST_REGISTRATION: TraceRegistration | None = None
_INSTALLED_TRACE_FUNCTION_ID: int | None = None


def _trace_log_method(
    self: logging.Logger,
    msg: object,
    *args: object,
    exc_info: Any = None,
    stack_info: bool = False,
    stacklevel: int = 1,
    extra: dict[str, Any] | None = None,
    **kwargs: Any,
) -> None:
    """Implementation installed as ``logging.Logger.trace``.

    The shape follows ``Logger.debug`` closely.  The method checks
    ``isEnabledFor`` before delegating to ``Logger._log`` so handler filtering,
    logger effective levels, propagation, ``exc_info``, ``extra``, stack info,
    and caller stack levels keep their standard logging behavior.
    """

    if self.isEnabledFor(TRACE_LEVEL):
        self._log(
            TRACE_LEVEL,
            msg,
            args,
            exc_info=exc_info,
            extra=extra,
            stack_info=stack_info,
            stacklevel=stacklevel,
            **kwargs,
        )


def _level_name_for(level: int) -> str | None:
    """Return the registered name for ``level`` when it is string-backed."""

    name = logging.getLevelName(level)
    return name if isinstance(name, str) else None


def _level_value_for(name: str) -> int | None:
    """Return the registered value for ``name`` when it is int-backed."""

    value = logging.getLevelName(name)
    return value if isinstance(value, int) else None


def _validate_trace_constants(level: int, name: str) -> None:
    """Reject constants that would not behave like a logging level."""

    if isinstance(level, bool) or not isinstance(level, int):
        raise TraceRegistrationError("TRACE level must be an integer, not bool.")
    if level <= 0:
        raise TraceRegistrationError("TRACE level must be greater than zero.")
    if not isinstance(name, str) or not name.strip():
        raise TraceRegistrationError("TRACE level name must be a non-empty string.")
    if name != name.upper():
        raise TraceRegistrationError("TRACE level name must be uppercase.")


def _logging_level_conflict(level: int, name: str) -> str | None:
    """Return a conflict message if another level already occupies TRACE space."""

    current_name = _level_name_for(level)
    if current_name and not current_name.startswith(f"Level {level}"):
        if current_name != name:
            return f"logging level {level} is already named {current_name!r}."

    current_value = _level_value_for(name)
    if current_value is not None and current_value != level:
        return f"logging level name {name!r} is already value {current_value!r}."

    return None


def _logger_trace_attribute() -> object | None:
    """Return the raw class attribute currently named ``trace``."""

    return getattr(logging.Logger, _TRACE_METHOD_NAME, None)


def _trace_method_matches_installed(attribute: object) -> bool:
    """Return whether ``attribute`` is the function this module installed."""

    return callable(attribute) and id(attribute) == _INSTALLED_TRACE_FUNCTION_ID


def _trace_method_is_compatible(attribute: object) -> bool:
    """Return whether an existing ``trace`` method can be accepted.

    A previous importer may already have installed an equivalent method.  We do
    not replace it if TRACE is already registered correctly, because monkey
    patching someone else's method would be surprising.  Compatibility here is
    intentionally conservative: callable is enough for idempotent coexistence.
    """

    return callable(attribute)


def _build_registration(level_added: bool, method_added: bool) -> TraceRegistration:
    """Create a result object for the latest registration call."""

    return TraceRegistration(
        level=TRACE_LEVEL,
        name=TRACE_NAME,
        level_added=level_added,
        method_added=method_added,
        already_registered=not level_added and not method_added,
    )


def register_trace_level(*, fail_on_conflict: bool = True) -> TraceRegistration:
    """Register TRACE and install ``logging.Logger.trace`` idempotently.

    Args:
        fail_on_conflict: When true, conflicting existing logging registrations
            raise ``TraceRegistrationError``.  When false, this function still
            refuses to overwrite the conflict, but returns the last successful
            registration if one exists.

    Returns:
        A ``TraceRegistration`` describing what this call changed.

    Raises:
        TraceRegistrationError: If TRACE constants are invalid, if another level
            owns value ``5`` or name ``TRACE``, or if an existing non-callable
            ``Logger.trace`` attribute blocks method installation.
    """

    global _TRACE_REGISTERED, _LAST_REGISTRATION, _INSTALLED_TRACE_FUNCTION_ID

    with _TRACE_LOCK:
        _validate_trace_constants(TRACE_LEVEL, TRACE_NAME)

        conflict = _logging_level_conflict(TRACE_LEVEL, TRACE_NAME)
        if conflict is not None:
            if fail_on_conflict or _LAST_REGISTRATION is None:
                raise TraceRegistrationError(conflict)
            return _LAST_REGISTRATION

        current_name = _level_name_for(TRACE_LEVEL)
        current_value = _level_value_for(TRACE_NAME)
        level_already_added = current_name == TRACE_NAME and current_value == TRACE_LEVEL

        level_added = False
        if not level_already_added:
            logging.addLevelName(TRACE_LEVEL, TRACE_NAME)
            level_added = True

        attribute = _logger_trace_attribute()
        method_added = False
        if attribute is None:
            setattr(logging.Logger, _TRACE_METHOD_NAME, _trace_log_method)
            _INSTALLED_TRACE_FUNCTION_ID = id(_trace_log_method)
            method_added = True
        elif _trace_method_matches_installed(attribute):
            pass
        elif _trace_method_is_compatible(attribute):
            if _INSTALLED_TRACE_FUNCTION_ID is None and attribute is _trace_log_method:
                _INSTALLED_TRACE_FUNCTION_ID = id(_trace_log_method)
        else:
            message = "logging.Logger.trace exists but is not callable."
            if fail_on_conflict:
                raise TraceRegistrationError(message)
            if _LAST_REGISTRATION is None:
                raise TraceRegistrationError(message)
            return _LAST_REGISTRATION

        _TRACE_REGISTERED = True
        _LAST_REGISTRATION = _build_registration(level_added, method_added)
        return _LAST_REGISTRATION


def unregister_trace_method_for_tests() -> None:
    """Remove this module's trace method when a test must reset monkey patches.

    The logging level-name mapping cannot be removed through public logging APIs,
    so this helper only removes ``Logger.trace`` when this module installed it.
    Application code should not call this during normal runtime.
    """

    global _TRACE_REGISTERED, _LAST_REGISTRATION, _INSTALLED_TRACE_FUNCTION_ID

    with _TRACE_LOCK:
        attribute = _logger_trace_attribute()
        if attribute is not None and _trace_method_matches_installed(attribute):
            delattr(logging.Logger, _TRACE_METHOD_NAME)
        _TRACE_REGISTERED = False
        _LAST_REGISTRATION = None
        _INSTALLED_TRACE_FUNCTION_ID = None


def is_trace_registered() -> bool:
    """Return true when logging knows TRACE and ``Logger.trace`` is callable."""

    with _TRACE_LOCK:
        return (
            _level_name_for(TRACE_LEVEL) == TRACE_NAME
            and _level_value_for(TRACE_NAME) == TRACE_LEVEL
            and callable(_logger_trace_attribute())
        )


def get_trace_registration() -> TraceRegistration:
    """Return current TRACE registration state, registering it if needed."""

    with _TRACE_LOCK:
        if _LAST_REGISTRATION is not None and is_trace_registered():
            return _LAST_REGISTRATION
    return register_trace_level()


def trace_level_value(*, register: bool = True) -> int:
    """Return the numeric TRACE level, optionally ensuring registration first."""

    if register:
        register_trace_level()
    return TRACE_LEVEL


def trace_level_name(*, register: bool = True) -> str:
    """Return the canonical TRACE level name, optionally registering it first."""

    if register:
        register_trace_level()
    return TRACE_NAME


def has_trace_method(logger: object) -> TypeGuard[logging.Logger]:
    """Return true when ``logger`` is a ``logging.Logger`` with trace support."""

    return isinstance(logger, logging.Logger) and callable(
        getattr(logger, _TRACE_METHOD_NAME, None)
    )


def ensure_trace_logger(
    logger: logging.Logger | str | None = None,
    *,
    set_level: bool = False,
) -> logging.Logger:
    """Return a logger that can emit ``logger.trace(...)``.

    Args:
        logger: A ``logging.Logger`` instance, a logger name, or ``None`` for the
            root logger.
        set_level: When true, set the selected logger level to ``TRACE``.  This
            is useful for tests or very verbose app profiles; most production
            setup should configure levels elsewhere.
    """

    register_trace_level()

    if logger is None:
        selected = logging.getLogger()
    elif isinstance(logger, str):
        selected = logging.getLogger(logger)
    elif isinstance(logger, logging.Logger):
        selected = logger
    else:
        raise TypeError(
            "logger must be logging.Logger, str, or None, "
            f"got {type(logger).__name__}."
        )

    if set_level:
        selected.setLevel(TRACE_LEVEL)
    return selected


def emit_trace(
    logger: logging.Logger | str | None,
    message: object,
    *args: object,
    **kwargs: Any,
) -> None:
    """Register TRACE and emit one trace message through a selected logger."""

    selected = ensure_trace_logger(logger)
    trace_method = getattr(selected, _TRACE_METHOD_NAME)
    cast(TraceLoggerProtocol, selected).trace(message, *args, **kwargs)
    if not isinstance(trace_method, MethodType) and not callable(trace_method):
        raise TraceRegistrationError("Logger.trace was not callable after registration.")


def trace_registration_summary() -> dict[str, object]:
    """Return a compact diagnostic dict for startup logs or tests."""

    registration = get_trace_registration()
    return {
        **registration.as_dict(),
        "loggingNameForValue": logging.getLevelName(TRACE_LEVEL),
        "loggingValueForName": logging.getLevelName(TRACE_NAME),
        "loggerTraceCallable": callable(_logger_trace_attribute()),
    }


def make_trace_record(
    logger_name: str,
    message: object,
    *args: object,
    **kwargs: Any,
) -> logging.LogRecord:
    """Build a TRACE ``LogRecord`` without emitting it.

    This is handy for tests and formatter previews that need a real standard
    logging record while keeping handlers untouched.
    """

    if not isinstance(logger_name, str) or not logger_name:
        raise ValueError("logger_name must be a non-empty string.")

    register_trace_level()
    logger = logging.getLogger(logger_name)
    return logger.makeRecord(
        logger.name,
        TRACE_LEVEL,
        fn=kwargs.pop("fn", ""),
        lno=kwargs.pop("lno", 0),
        msg=message,
        args=args,
        exc_info=kwargs.pop("exc_info", None),
        func=kwargs.pop("func", None),
        extra=kwargs.pop("extra", None),
        sinfo=kwargs.pop("sinfo", None),
        **kwargs,
    )


__all__ = [
    "TRACE_LEVEL",
    "TRACE_NAME",
    "TraceLoggerProtocol",
    "TraceRegistration",
    "TraceRegistrationError",
    "emit_trace",
    "ensure_trace_logger",
    "get_trace_registration",
    "has_trace_method",
    "is_trace_registered",
    "make_trace_record",
    "register_trace_level",
    "trace_level_name",
    "trace_level_value",
    "trace_registration_summary",
    "unregister_trace_method_for_tests",
]
