from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import random
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from abc_discord_bridge import AbcDiscordBridge, normalize_discord_channel_id
from ai_api import create_ai_router
from codex_bridge import CodexPowanBridge
from powan_store import PowanStore


APP_ROOT = Path(__file__).resolve().parent
STATIC_ROOT = APP_ROOT / "static"
POWAN_WORK_ROOT = APP_ROOT / "powan_work"
SETTING_ROOT = APP_ROOT / "setting"
DEFAULT_SOUND_ROOT = SETTING_ROOT / "sound"
SETTINGS_PATH = SETTING_ROOT / "settings.json"
LOG_ROOT = APP_ROOT / "logs"
CLIENT_LOG_PATH = LOG_ROOT / "abc_canvas.log"
RESTART_LOG_PATH = LOG_ROOT / "abc_canvas_restart.log"
START_SCRIPT_PATH = APP_ROOT / "start_abc_canvas.bat"
DEFAULT_FILE = "project.powan"
SOUND_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"}
INLINE_IMAGE_MAX_BYTES = 25 * 1024 * 1024
IMAGE_MIME_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
DEFAULT_CONVERSATION_SOUND_VOLUME = 0.55
DEFAULT_INPUT_SOUND_VOLUME = 0.55
DEFAULT_AUTO_SUMMARY_ENABLED = True
DEFAULT_AUTO_SUMMARY_TURNS = 50
MIN_AUTO_SUMMARY_TURNS = 2
MAX_AUTO_SUMMARY_TURNS = 500
DEFAULT_CODEX_SANDBOX = "danger-full-access"
CODEX_SANDBOXES = {"read-only", "workspace-write", "danger-full-access"}
DEFAULT_CODEX_MODEL = "gpt-5.5"
DEFAULT_CODEX_REASONING_EFFORT = "low"
CODEX_REASONING_EFFORTS = {"", "none", "minimal", "low", "medium", "high", "xhigh"}
CODEX_REASONING_EFFORT_ALIASES = {
    "very_high": "xhigh",
    "very-high": "xhigh",
}
DEFAULT_DISCORD_TOKEN_ENV = "DISCORD_BOT_TOKEN"
DEFAULT_DISCORD_MESSAGE_LIMIT = 1900
DEFAULT_ARRANGE_SPACING = 1.0
DEFAULT_ARRANGE_SIZE = 1.0
MIN_ARRANGE_SPACING = 0.3
MAX_ARRANGE_SPACING = 3.0
MIN_ARRANGE_SIZE = 0.3
MAX_ARRANGE_SIZE = 2.5
TITLE_FONT_FAMILIES = {
    "",
    "Dela Gothic One",
    "Hachi Maru Pop",
    "Klee One",
    "RocknRoll One",
    "New Tegomin",
    "Train One",
    "DotGothic16",
    "Reggae One",
    "Yuji Syuku",
    "Yuji Boku",
    "Mochiy Pop One",
    "Kaisei HarunoUmi",
    "Shippori Antique",
    "Stick",
    "Rampart One",
    "Zen Antique",
    "Mochiy Pop P One",
    "Zen Kurenaido",
    "Yusei Magic",
}
DEFAULT_TITLE_FONT_FAMILY = ""
DEFAULT_TITLE_FONT_SCALE = 1.0
MIN_TITLE_FONT_SCALE = 0.5
MAX_TITLE_FONT_SCALE = 2.0
DEFAULT_TITLE_OUTLINE_COLOR = "#ffffff"
DEFAULT_TITLE_OUTLINE_WIDTH = 1.5
MIN_TITLE_OUTLINE_WIDTH = 0.0
MAX_TITLE_OUTLINE_WIDTH = 6.0
DEFAULT_TITLE_SHADOW_COLOR = "#ffffff"
DEFAULT_TITLE_SHADOW_BLUR = 4.0
MIN_TITLE_SHADOW_BLUR = 0.0
MAX_TITLE_SHADOW_BLUR = 18.0
MIN_TITLE_SHADOW_OFFSET = -12.0
MAX_TITLE_SHADOW_OFFSET = 12.0
WORKSPACE_SIZE = 10000
WORKSPACE_ORIGIN_X = 5000
WORKSPACE_ORIGIN_Y = 5000
DEFAULT_NODE_WIDTH = 280
DEFAULT_NODE_HEIGHT = 160
CONSOLE_TEXT_PREVIEW_CHARS = 30
LOG_LEVEL_NAMES = ("trace", "debug", "info", "warn", "error", "fatal")
DEFAULT_CONSOLE_LOG_LEVELS = ("info", "warn", "error")
POWAN_WORK_EVENT_LIMIT = 500
POWAN_COLOR_PALETTE = [
    {"color": "#fff1b8", "accent": "#d8b500"},
    {"color": "#ffe1ef", "accent": "#ef6ea8"},
    {"color": "#dcf7ff", "accent": "#34a6cf"},
    {"color": "#e5f8c8", "accent": "#7db83f"},
    {"color": "#efe3ff", "accent": "#9b72df"},
    {"color": "#ffe7c7", "accent": "#ef9a3c"},
    {"color": "#dff7ec", "accent": "#42b883"},
    {"color": "#e2ecff", "accent": "#5f8fe8"},
]

POWAN_WORK_ROOT.mkdir(parents=True, exist_ok=True)
SETTING_ROOT.mkdir(parents=True, exist_ok=True)
DEFAULT_SOUND_ROOT.mkdir(parents=True, exist_ok=True)
LOG_ROOT.mkdir(parents=True, exist_ok=True)

POWAN_WORK_EVENTS: list[dict[str, Any]] = []
POWAN_WORK_EVENT_SEQUENCE = 0
POWAN_WORK_EVENT_LOCK = threading.Lock()
COMMAND_CHILDREN_ACTIVE_LOCK = threading.Lock()
COMMAND_CHILDREN_ACTIVE_KEYS: set[str] = set()


def reset_logs() -> None:
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    for path in LOG_ROOT.glob("*.log"):
        if path.is_file() and path != RESTART_LOG_PATH:
            path.unlink()
    CLIENT_LOG_PATH.write_text("", encoding="utf-8")


def write_log_entries(entries: list[dict[str, Any]]) -> int:
    if not entries:
        return 0
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    server_time = datetime.now().isoformat(timespec="milliseconds")
    lines = [
        json.dumps(
            {
                "serverTime": server_time,
                "entry": entry,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        for entry in entries
    ]
    with CLIENT_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return len(lines)


def compact_console_text(value: Any, limit: int = CONSOLE_TEXT_PREVIEW_CHARS) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]


def console_preview_text(details: dict[str, Any] | None) -> str:
    if not details:
        return ""
    for key in ("textPreview", "instructionPreview", "error", "detail"):
        value = details.get(key)
        if value:
            return compact_console_text(value)
    return ""


def normalize_console_log_levels(value: Any) -> list[str]:
    if not isinstance(value, list):
        return list(DEFAULT_CONSOLE_LOG_LEVELS)
    values = {str(item).lower() for item in value}
    levels = [level for level in LOG_LEVEL_NAMES if level in values]
    return levels or list(DEFAULT_CONSOLE_LOG_LEVELS)


def current_console_log_levels() -> list[str]:
    if not SETTINGS_PATH.exists():
        return list(DEFAULT_CONSOLE_LOG_LEVELS)
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return list(DEFAULT_CONSOLE_LOG_LEVELS)
    return normalize_console_log_levels(data.get("consoleLogLevels"))


def should_print_server_event(level: str, details: dict[str, Any] | None) -> bool:
    return level.lower() in set(current_console_log_levels())


def print_server_event(level: str, action: str, details: dict[str, Any] | None) -> None:
    message = str((details or {}).get("message") or "")
    preview = console_preview_text(details)
    suffix = f' "{preview}"' if preview else ""
    print(f"{datetime.now().isoformat(timespec='seconds')} {level.upper()} {action} {message}{suffix}", flush=True)


def log_server_event(level: str, action: str, details: dict[str, Any] | None = None) -> None:
    write_log_entries(
        [
            {
                "level": level,
                "action": action,
                "source": "server",
                "pid": os.getpid(),
                **(details or {}),
            }
        ]
    )
    if should_print_server_event(level, details):
        print_server_event(level, action, details)


reset_logs()
log_server_event("info", "server-startup", {"appRoot": str(APP_ROOT)})


class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: dict[str, Any]):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


def no_cache_file(path: Path) -> FileResponse:
    return FileResponse(
        path,
        headers={
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


app = FastAPI(title="ABC Canvas")
app.mount("/static", NoCacheStaticFiles(directory=STATIC_ROOT), name="static")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    log_server_event(
        "warn",
        "request-validation-error",
        {
            "method": request.method,
            "path": request.url.path,
            "errors": exc.errors(),
        },
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


class AbcDocument(BaseModel):
    version: int = 1
    canvas: dict[str, Any] = Field(default_factory=dict)
    nodes: list[dict[str, Any]] = Field(default_factory=list)


class ProjectCreateRequest(BaseModel):
    name: str


class ClientLogBatch(BaseModel):
    entries: list[dict[str, Any]] = Field(default_factory=list)


class ShutdownRequest(BaseModel):
    reason: str = "frontend"


class RestartRequest(BaseModel):
    reason: str = "frontend"
    visibleConsole: bool | None = None


class SoundFolderRequest(BaseModel):
    soundRoot: str


class ConversationSoundRequest(BaseModel):
    conversationSound: str = ""


class ConversationSoundVolumeRequest(BaseModel):
    conversationSoundVolume: float


class InputSoundRequest(BaseModel):
    inputSound: str = ""


class InputSoundVolumeRequest(BaseModel):
    inputSoundVolume: float


class ConversationAutoSummaryRequest(BaseModel):
    enabled: bool
    turns: int


class CodexSandboxRequest(BaseModel):
    codexSandbox: str


class CodexModelSettingsRequest(BaseModel):
    codexModel: str = ""
    codexReasoningEffort: str = ""


class DiscordSettingsRequest(BaseModel):
    enabled: bool = False
    tokenEnv: str = DEFAULT_DISCORD_TOKEN_ENV
    channelId: str = ""
    project: str = ""
    file: str = DEFAULT_FILE
    targetNodeId: str = ""
    messageLimit: int = DEFAULT_DISCORD_MESSAGE_LIMIT


class ArrangeSettingsRequest(BaseModel):
    arrangeSpacing: float
    arrangeSize: float
    arrangeResizeParents: bool = True
    arrangeRecursive: bool = True
    arrangeChildSpacing: float | None = None
    arrangeChildSize: float | None = None
    arrangeNestedChildSize: float | None = None
    arrangeWorldParentSpacing: float | None = None
    arrangeWorldParentSize: float | None = None
    nestedLayerScale: float | None = None


class ConsoleLogSettingsRequest(BaseModel):
    consoleLogLevels: list[str] = Field(default_factory=list)


class RestartVisibleConsoleSettingsRequest(BaseModel):
    restartVisibleConsole: bool = False


class TitleStyleSettingsRequest(BaseModel):
    titleFontFamily: str = DEFAULT_TITLE_FONT_FAMILY
    titleFontScale: float = DEFAULT_TITLE_FONT_SCALE
    titleOutlineEnabled: bool = False
    titleOutlineColor: str = DEFAULT_TITLE_OUTLINE_COLOR
    titleOutlineWidth: float = DEFAULT_TITLE_OUTLINE_WIDTH
    titleShadowEnabled: bool = True
    titleShadowColor: str = DEFAULT_TITLE_SHADOW_COLOR
    titleShadowBlur: float = DEFAULT_TITLE_SHADOW_BLUR
    titleShadowX: float = 0.0
    titleShadowY: float = 1.0


class ConversationMessageRequest(BaseModel):
    role: str = "user"
    text: str


class PowanCodexRequest(BaseModel):
    text: str
    includeMeaningTree: bool = False
    includeDirectChildCode: bool = False
    attachments: list[dict[str, Any]] = Field(default_factory=list)


class ChildCommandRequest(BaseModel):
    title: str = ""
    body: str = ""
    childId: str | None = None
    instruction: str = ""
    skip: bool = False
    skipReason: str = ""
    status: str = ""


class CommandChildrenRequest(BaseModel):
    project: str
    file: str = DEFAULT_FILE
    instruction: str = ""
    instructions: list[ChildCommandRequest] = Field(default_factory=list)
    bulkHistoryId: str = ""
    includeMeaningTree: bool = False
    continueAfterChildReplies: bool = False


class BulkCommandHistoryMessage(BaseModel):
    role: str = "system"
    text: str = ""
    createdAt: str = ""


class BulkCommandHistoryRequest(BaseModel):
    project: str
    file: str = DEFAULT_FILE
    id: str
    targetIds: list[str] = Field(default_factory=list)
    targetNames: list[str] = Field(default_factory=list)
    messages: list[BulkCommandHistoryMessage] = Field(default_factory=list)
    createdAt: str = ""
    updatedAt: str = ""


def base_model_payload(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return model.dict()


def record_api_action_safely(
    *,
    project: str,
    file: str,
    node_id: str | None,
    action: str,
    status: str,
    request_payload: dict[str, Any] | list[Any] | None = None,
    response_payload: dict[str, Any] | list[Any] | None = None,
    error_text: str = "",
) -> None:
    try:
        STORE.record_api_action(
            project,
            file,
            node_id,
            action,
            status,
            request_payload=request_payload,
            response_payload=response_payload,
            error_text=error_text,
        )
    except Exception as exc:
        log_server_event(
            "error",
            "powan-api-action-log-failed",
            {
                "project": project,
                "file": file,
                "nodeId": node_id,
                "action": action,
                "status": status,
                "error": repr(exc),
                "request": request_payload or {},
                "response": response_payload or {},
            },
        )


def conversation_attachment_lines(attachments: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for attachment in attachments[:20]:
        if not isinstance(attachment, dict):
            continue
        kind = str(attachment.get("kind") or "file")
        name = str(attachment.get("name") or attachment.get("host") or attachment.get("url") or "attachment")
        path = str(attachment.get("path") or "")
        url = str(attachment.get("url") or "")
        if path:
            lines.append(f"- {kind}: {name}\n  path: {path}")
        elif url:
            lines.append(f"- {kind}: {name}\n  url: {url}")
        else:
            lines.append(f"- {kind}: {name}\n  path: （ブラウザから取得できない）")
    return lines


def conversation_record_text(text: str, attachments: list[dict[str, Any]]) -> str:
    parts = []
    clean_text = text.strip()
    if clean_text:
        parts.append(clean_text)
    attachment_lines = conversation_attachment_lines(attachments)
    if attachment_lines:
        parts.append("添付:\n" + "\n".join(attachment_lines))
    return "\n\n".join(parts) or "添付を渡す"


def windows_process_summary(pid: int) -> dict[str, Any] | None:
    if os.name != "nt":
        return None
    script = (
        f"$p = Get-CimInstance Win32_Process -Filter \"ProcessId = {pid}\"; "
        "if ($p) { "
        "[pscustomobject]@{ProcessId=$p.ProcessId;ParentProcessId=$p.ParentProcessId;Name=$p.Name;CommandLine=$p.CommandLine} | ConvertTo-Json -Compress "
        "}"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def should_shutdown_parent(pid: int) -> bool:
    info = windows_process_summary(pid)
    if not info:
        return False
    name = str(info.get("Name") or "").lower()
    command = str(info.get("CommandLine") or "").lower()
    return "python" in name and "uvicorn" in command and "app:app" in command and ("8790" in command or "abc_canvas" in command)


def should_shutdown_batch_shell(pid: int) -> bool:
    info = windows_process_summary(pid)
    if not info:
        return False
    name = str(info.get("Name") or "").lower()
    command = str(info.get("CommandLine") or "").lower()
    return name == "cmd.exe" and "start_abc_canvas.bat" in command


def shutdown_target_pids() -> list[int]:
    pids = [os.getpid()]
    parent_pid = os.getppid()
    if parent_pid and parent_pid not in pids and should_shutdown_parent(parent_pid):
        pids.append(parent_pid)
        parent_info = windows_process_summary(parent_pid) or {}
        grandparent_pid = int(parent_info.get("ParentProcessId") or 0)
        if grandparent_pid and grandparent_pid not in pids and should_shutdown_batch_shell(grandparent_pid):
            pids.append(grandparent_pid)
    return pids


def shutdown_later(pids: list[int]) -> None:
    time.sleep(0.35)
    log_server_event("info", "shutdown-execute", {"targetPids": pids})
    if os.name == "nt":
        args = ["taskkill"]
        for pid in pids:
            args.extend(["/PID", str(pid)])
        args.extend(["/T", "/F"])
        subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return
    os._exit(0)


def restart_helper_code() -> str:
    return r"""
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

app_root = Path(os.environ["ABC_CANVAS_RESTART_ROOT"])
python_exe = os.environ.get("ABC_CANVAS_RESTART_PYTHON") or sys.executable
log_path = os.environ.get("ABC_CANVAS_RESTART_LOG")
start_script = Path(os.environ.get("ABC_CANVAS_RESTART_START_SCRIPT") or "")
visible_console = os.environ.get("ABC_CANVAS_RESTART_VISIBLE_CONSOLE") == "1"


def helper_log(action, **details):
    if not log_path:
        return
    entry = {
        "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "action": action,
        **details,
    }
    try:
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


try:
    helper_log("restart-helper-start", appRoot=str(app_root), python=python_exe, visibleConsole=visible_console)
    deadline = time.time() + 12
    port_busy = True
    while time.time() < deadline:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.2)
        try:
            port_busy = sock.connect_ex(("127.0.0.1", 8790)) == 0
        finally:
            sock.close()
        if not port_busy:
            helper_log("restart-helper-port-free")
            break
        time.sleep(0.25)
    if port_busy:
        helper_log("restart-helper-port-wait-timeout")
    time.sleep(0.25)
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    if visible_console and os.name == "nt" and start_script.exists():
        process = subprocess.Popen(
            [str(start_script)],
            cwd=str(app_root),
            env=env,
            creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
        )
        helper_log("restart-helper-visible-cmd-started", pid=process.pid, startScript=str(start_script))
    else:
        flags = 0
        if os.name == "nt":
            flags = (
                getattr(subprocess, "CREATE_NO_WINDOW", 0)
                | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                | getattr(subprocess, "DETACHED_PROCESS", 0)
            )
        process = subprocess.Popen(
            [python_exe, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8790", "--no-access-log"],
            cwd=str(app_root),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
        helper_log("restart-helper-hidden-uvicorn-started", pid=process.pid)
except Exception as exc:
    helper_log("restart-helper-error", error=repr(exc))
    raise
"""


def launch_restart_helper(visible_console: bool = False) -> int | None:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["ABC_CANVAS_RESTART_ROOT"] = str(APP_ROOT)
    env["ABC_CANVAS_RESTART_PYTHON"] = sys.executable
    env["ABC_CANVAS_RESTART_LOG"] = str(RESTART_LOG_PATH)
    env["ABC_CANVAS_RESTART_START_SCRIPT"] = str(START_SCRIPT_PATH)
    env["ABC_CANVAS_RESTART_VISIBLE_CONSOLE"] = "1" if visible_console else "0"
    flags = 0
    if os.name == "nt":
        flags = (
            getattr(subprocess, "CREATE_NO_WINDOW", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
        )
    log_server_event(
        "info",
        "restart-helper-launch",
        {
            "python": sys.executable,
            "appRoot": str(APP_ROOT),
            "restartLog": str(RESTART_LOG_PATH),
            "visibleConsole": bool(visible_console),
            "startScript": str(START_SCRIPT_PATH),
        },
    )
    try:
        process = subprocess.Popen(
            [sys.executable, "-c", restart_helper_code()],
            cwd=str(APP_ROOT),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
    except OSError as exc:
        log_server_event(
            "error",
            "restart-helper-launch-failed",
            {"error": str(exc), "restartLog": str(RESTART_LOG_PATH), "visibleConsole": bool(visible_console)},
        )
        return None
    log_server_event(
        "info",
        "restart-helper-launched",
        {"helperPid": process.pid, "restartLog": str(RESTART_LOG_PATH), "visibleConsole": bool(visible_console)},
    )
    return process.pid


def kill_pids_later(pids: list[int], *, tree: bool) -> None:
    time.sleep(0.35)
    if os.name == "nt":
        args = ["taskkill"]
        for pid in pids:
            args.extend(["/PID", str(pid)])
        if tree:
            args.append("/T")
        args.append("/F")
        log_server_event("info", "restart-kill-targets", {"targetPids": pids, "tree": tree})
        subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return
    os._exit(0)


def restart_later(pids: list[int], visible_console: bool = False) -> None:
    helper_pid = launch_restart_helper(visible_console=visible_console)
    if helper_pid is None:
        log_server_event(
            "error",
            "restart-aborted",
            {"reason": "helper launch failed", "targetPids": pids, "visibleConsole": bool(visible_console)},
        )
        return
    log_server_event(
        "info",
        "restart-kill-old-server",
        {"helperPid": helper_pid, "targetPids": pids, "visibleConsole": bool(visible_console)},
    )
    kill_pids_later(pids, tree=False)


def safe_project_name(name: str) -> str:
    candidate = name.strip()
    if not candidate:
        raise HTTPException(status_code=400, detail="Project name is required")
    if Path(candidate).name != candidate or any(part in candidate for part in ("/", "\\")):
        raise HTTPException(status_code=400, detail="Invalid project name")
    invalid_chars = set('<>:"|?*')
    if any(char in invalid_chars or ord(char) < 32 for char in candidate):
        raise HTTPException(status_code=400, detail="Invalid project name")
    if candidate in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid project name")
    return candidate


def safe_powan_name(name: str) -> str:
    safe_name = Path(name).name
    if not safe_name.endswith(".powan"):
        safe_name += ".powan"
    if safe_name in {".powan", "..powan"}:
        raise HTTPException(status_code=400, detail="Invalid powan file name")
    return safe_name


def project_root(name: str) -> Path:
    safe_name = safe_project_name(name)
    path = (POWAN_WORK_ROOT / safe_name).resolve()
    if POWAN_WORK_ROOT.resolve() not in path.parents and path != POWAN_WORK_ROOT.resolve():
        raise HTTPException(status_code=400, detail="Invalid project path")
    return path


def powan_path(project: str, name: str = DEFAULT_FILE) -> Path:
    root = project_root(project)
    path = (root / safe_powan_name(name)).resolve()
    if root not in path.parents and path != root:
        raise HTTPException(status_code=400, detail="Invalid file path")
    return path


def safe_attachment_stem(name: str) -> str:
    stem = Path(name or "clipboard").stem.strip() or "clipboard"
    invalid_chars = set('<>:"/\\|?*')
    cleaned = "".join("_" if char in invalid_chars or ord(char) < 32 else char for char in stem)
    cleaned = " ".join(cleaned.split()).strip(" .")
    return (cleaned or "clipboard")[:80]


def split_image_data_url(data_url: str) -> tuple[str, bytes]:
    header, separator, encoded = data_url.partition(",")
    if not separator or not header.lower().startswith("data:image/") or ";base64" not in header.lower():
        raise HTTPException(status_code=400, detail="Invalid image data")
    mime = header[5:].split(";", 1)[0].lower()
    if mime not in IMAGE_MIME_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported image type")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid image data") from exc
    if len(raw) > INLINE_IMAGE_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Image is too large")
    return mime, raw


def save_inline_image_attachment(project: str, attachment: dict[str, Any], data_url: str) -> dict[str, Any]:
    mime, raw = split_image_data_url(data_url)
    root = project_root(project).resolve()
    attachment_root = (root / "data" / "attachments").resolve()
    if root not in attachment_root.parents and attachment_root != root:
        raise HTTPException(status_code=400, detail="Invalid attachment path")
    attachment_root.mkdir(parents=True, exist_ok=True)
    stem = safe_attachment_stem(str(attachment.get("name") or "clipboard"))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{uuid4().hex[:10]}_{stem}{IMAGE_MIME_EXTENSIONS[mime]}"
    path = (attachment_root / filename).resolve()
    if attachment_root not in path.parents:
        raise HTTPException(status_code=400, detail="Invalid attachment path")
    path.write_bytes(raw)
    relative_path = path.relative_to(root).as_posix()
    next_attachment = dict(attachment)
    next_attachment.pop("imageDataUrl", None)
    next_attachment.update(
        {
            "kind": "image",
            "source": str(next_attachment.get("source") or "clipboard"),
            "name": str(next_attachment.get("name") or filename),
            "mime": mime,
            "size": len(raw),
            "path": str(path),
            "relativePath": relative_path,
            "pathAvailable": True,
        }
    )
    log_server_event(
        "info",
        "conversation-inline-image-saved",
        {
            "project": safe_project_name(project),
            "name": next_attachment["name"],
            "relativePath": relative_path,
            "size": len(raw),
        },
    )
    return next_attachment


def materialize_conversation_attachments(project: str, attachments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    materialized: list[dict[str, Any]] = []
    for attachment in attachments[:20]:
        if not isinstance(attachment, dict):
            continue
        next_attachment = dict(attachment)
        data_url = str(next_attachment.get("imageDataUrl") or "")
        if data_url:
            next_attachment = save_inline_image_attachment(project, next_attachment, data_url)
        else:
            next_attachment.pop("imageDataUrl", None)
        next_attachment["pathAvailable"] = bool(next_attachment.get("path"))
        materialized.append(next_attachment)
    return materialized


def safe_sound_name(name: str) -> str:
    safe_name = Path(name).name
    if safe_name != name or not safe_name:
        raise HTTPException(status_code=400, detail="Invalid sound file name")
    if Path(safe_name).suffix.lower() not in SOUND_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported sound file")
    return safe_name


def resolve_sound_root(value: str | None) -> Path:
    raw = str(value or "").strip()
    path = DEFAULT_SOUND_ROOT if not raw else Path(raw).expanduser()
    if not path.is_absolute():
        path = APP_ROOT / path
    return path.resolve()


def ensure_sound_root(path: Path) -> Path:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"Sound folder cannot be created: {exc}") from exc
    if not path.is_dir():
        raise HTTPException(status_code=400, detail="Sound root is not a folder")
    return path


def clamp_sound_volume(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = DEFAULT_CONVERSATION_SOUND_VOLUME
    return min(1.0, max(0.0, number))


def clamp_auto_summary_turns(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = DEFAULT_AUTO_SUMMARY_TURNS
    return min(MAX_AUTO_SUMMARY_TURNS, max(MIN_AUTO_SUMMARY_TURNS, number))


def clamp_arrange_spacing(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = DEFAULT_ARRANGE_SPACING
    return min(MAX_ARRANGE_SPACING, max(MIN_ARRANGE_SPACING, number))


def clamp_arrange_size(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = DEFAULT_ARRANGE_SIZE
    return min(MAX_ARRANGE_SIZE, max(MIN_ARRANGE_SIZE, number))


def clamp_nested_layer_scale(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.5
    return min(1.0, max(0.3, number))


def normalize_title_font_family(value: Any) -> str:
    clean = str(value or "").strip()
    return clean if clean in TITLE_FONT_FAMILIES else DEFAULT_TITLE_FONT_FAMILY


def normalize_hex_color(value: Any, fallback: str = "#ffffff") -> str:
    clean = str(value or "").strip().lower()
    if len(clean) == 7 and clean.startswith("#") and all(char in "0123456789abcdef" for char in clean[1:]):
        return clean
    return fallback


def clamp_title_font_scale(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = DEFAULT_TITLE_FONT_SCALE
    return min(MAX_TITLE_FONT_SCALE, max(MIN_TITLE_FONT_SCALE, number))


def clamp_title_outline_width(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = DEFAULT_TITLE_OUTLINE_WIDTH
    return min(MAX_TITLE_OUTLINE_WIDTH, max(MIN_TITLE_OUTLINE_WIDTH, number))


def clamp_title_shadow_blur(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = DEFAULT_TITLE_SHADOW_BLUR
    return min(MAX_TITLE_SHADOW_BLUR, max(MIN_TITLE_SHADOW_BLUR, number))


def clamp_title_shadow_offset(value: Any, fallback: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = fallback
    return min(MAX_TITLE_SHADOW_OFFSET, max(MIN_TITLE_SHADOW_OFFSET, number))


def normalize_codex_sandbox(value: Any) -> str:
    sandbox = str(value or "").strip()
    return sandbox if sandbox in CODEX_SANDBOXES else DEFAULT_CODEX_SANDBOX


def normalize_codex_model(value: Any) -> str:
    model = str(value or "").strip()
    return model[:120]


def normalize_codex_reasoning_effort(value: Any) -> str:
    effort = str(value or "").strip().lower()
    effort = CODEX_REASONING_EFFORT_ALIASES.get(effort, effort)
    return effort if effort in CODEX_REASONING_EFFORTS else DEFAULT_CODEX_REASONING_EFFORT


def normalize_discord_message_limit(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = DEFAULT_DISCORD_MESSAGE_LIMIT
    return min(2000, max(300, number))


def normalize_discord_settings(value: Any) -> dict[str, Any]:
    data = value if isinstance(value, dict) else {}
    project = str(data.get("project") or "").strip()
    file = str(data.get("file") or DEFAULT_FILE).strip() or DEFAULT_FILE
    if not file.endswith(".powan"):
        file = f"{file}.powan"
    return {
        "enabled": bool(data.get("enabled", False)),
        "tokenEnv": DEFAULT_DISCORD_TOKEN_ENV,
        "channelId": normalize_discord_channel_id(data.get("channelId") or ""),
        "project": project,
        "file": Path(file).name,
        "targetNodeId": str(data.get("targetNodeId") or "").strip(),
        "messageLimit": normalize_discord_message_limit(data.get("messageLimit")),
    }


def stable_for_signature(value: Any) -> Any:
    if isinstance(value, list):
        return [stable_for_signature(item) for item in value]
    if isinstance(value, dict):
        return {key: stable_for_signature(value[key]) for key in sorted(value)}
    return value


def document_signature(document: dict[str, Any]) -> str:
    stable_json = json.dumps(stable_for_signature(document), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(stable_json.encode("utf-8")).hexdigest()


def powershell_single_quoted(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def pick_sound_folder_with_explorer(initial_path: Path) -> Path | None:
    if os.name != "nt":
        raise HTTPException(status_code=400, detail="Folder picker is only supported on Windows")
    script = f"""
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public static class ModernFolderPicker
{{
    [DllImport("shell32.dll", CharSet = CharSet.Unicode, PreserveSig = false)]
    private static extern void SHCreateItemFromParsingName(
        [MarshalAs(UnmanagedType.LPWStr)] string pszPath,
        IntPtr pbc,
        ref Guid riid,
        [MarshalAs(UnmanagedType.Interface)] out IShellItem ppv);

    [ComImport]
    [Guid("DC1C5A9C-E88A-4DDE-A5A1-60F82A20AEF7")]
    private class FileOpenDialogRCW
    {{
    }}

    [ComImport]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    [Guid("43826D1E-E718-42EE-BC55-A1E261C37BFE")]
    private interface IShellItem
    {{
        void BindToHandler(IntPtr pbc, ref Guid bhid, ref Guid riid, out IntPtr ppv);
        void GetParent(out IShellItem ppsi);
        void GetDisplayName(SIGDN sigdnName, [MarshalAs(UnmanagedType.LPWStr)] out string ppszName);
        void GetAttributes(uint sfgaoMask, out uint psfgaoAttribs);
        void Compare(IShellItem psi, uint hint, out int piOrder);
    }}

    private enum SIGDN : uint
    {{
        FILESYSPATH = 0x80058000
    }}

    [Flags]
    private enum FOS : uint
    {{
        PICKFOLDERS = 0x20,
        FORCEFILESYSTEM = 0x40,
        NOCHANGEDIR = 0x8,
        PATHMUSTEXIST = 0x800
    }}

    [ComImport]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    [Guid("D57C7288-D4AD-4768-BE02-9D969532D960")]
    private interface IFileOpenDialog
    {{
        [PreserveSig]
        int Show(IntPtr parent);
        void SetFileTypes(uint cFileTypes, IntPtr rgFilterSpec);
        void SetFileTypeIndex(uint iFileType);
        void GetFileTypeIndex(out uint piFileType);
        void Advise(IntPtr pfde, out uint pdwCookie);
        void Unadvise(uint dwCookie);
        void SetOptions(FOS fos);
        void GetOptions(out FOS pfos);
        void SetDefaultFolder(IShellItem psi);
        void SetFolder(IShellItem psi);
        void GetFolder(out IShellItem ppsi);
        void GetCurrentSelection(out IShellItem ppsi);
        void SetFileName([MarshalAs(UnmanagedType.LPWStr)] string pszName);
        void GetFileName([MarshalAs(UnmanagedType.LPWStr)] out string pszName);
        void SetTitle([MarshalAs(UnmanagedType.LPWStr)] string pszTitle);
        void SetOkButtonLabel([MarshalAs(UnmanagedType.LPWStr)] string pszText);
        void SetFileNameLabel([MarshalAs(UnmanagedType.LPWStr)] string pszLabel);
        void GetResult(out IShellItem ppsi);
        void AddPlace(IShellItem psi, uint fdap);
        void SetDefaultExtension([MarshalAs(UnmanagedType.LPWStr)] string pszDefaultExtension);
        void Close(int hr);
        void SetClientGuid(ref Guid guid);
        void ClearClientData();
        void SetFilter(IntPtr pFilter);
        void GetResults(out IntPtr ppenum);
        void GetSelectedItems(out IntPtr ppsai);
    }}

    public static string Pick(string title, string initialPath)
    {{
        IFileOpenDialog dialog = (IFileOpenDialog)new FileOpenDialogRCW();
        FOS options;
        dialog.GetOptions(out options);
        dialog.SetOptions(options | FOS.PICKFOLDERS | FOS.FORCEFILESYSTEM | FOS.PATHMUSTEXIST | FOS.NOCHANGEDIR);
        dialog.SetTitle(title);
        dialog.SetOkButtonLabel("このフォルダを使う");
        if (!String.IsNullOrWhiteSpace(initialPath) && System.IO.Directory.Exists(initialPath))
        {{
            Guid shellItemGuid = new Guid("43826D1E-E718-42EE-BC55-A1E261C37BFE");
            IShellItem folder;
            SHCreateItemFromParsingName(initialPath, IntPtr.Zero, ref shellItemGuid, out folder);
            dialog.SetFolder(folder);
        }}
        int hr = dialog.Show(IntPtr.Zero);
        const int errorCancelled = unchecked((int)0x800704C7);
        if (hr == errorCancelled)
        {{
            return "";
        }}
        if (hr != 0)
        {{
            Marshal.ThrowExceptionForHR(hr);
        }}
        IShellItem result;
        dialog.GetResult(out result);
        string path;
        result.GetDisplayName(SIGDN.FILESYSPATH, out path);
        return path ?? "";
    }}
}}
"@
[ModernFolderPicker]::Pick('ABC Canvas サウンドフォルダ', {powershell_single_quoted(str(initial_path))})
"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-STA", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=408, detail="Folder picker timed out") from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Folder picker failed: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "Folder picker failed").strip()
        raise HTTPException(status_code=500, detail=detail)
    selected = result.stdout.strip()
    if not selected:
        return None
    return Path(selected).resolve()


def load_app_settings() -> dict[str, Any]:
    data: dict[str, Any] = {}
    if SETTINGS_PATH.exists():
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log_server_event("warn", "settings-load-failed", {"message": str(exc)})
            data = {}
    try:
        sound_root = ensure_sound_root(resolve_sound_root(str(data.get("soundRoot") or "")))
    except HTTPException:
        sound_root = ensure_sound_root(DEFAULT_SOUND_ROOT.resolve())
    return {
        "soundRoot": str(sound_root),
        "conversationSound": str(data.get("conversationSound") or ""),
        "conversationSoundVolume": clamp_sound_volume(data.get("conversationSoundVolume", DEFAULT_CONVERSATION_SOUND_VOLUME)),
        "inputSound": str(data.get("inputSound") or ""),
        "inputSoundVolume": clamp_sound_volume(data.get("inputSoundVolume", DEFAULT_INPUT_SOUND_VOLUME)),
        "autoSummaryEnabled": bool(data.get("autoSummaryEnabled", DEFAULT_AUTO_SUMMARY_ENABLED)),
        "autoSummaryTurns": clamp_auto_summary_turns(data.get("autoSummaryTurns", DEFAULT_AUTO_SUMMARY_TURNS)),
        "codexSandbox": normalize_codex_sandbox(data.get("codexSandbox", DEFAULT_CODEX_SANDBOX)),
        "codexModel": normalize_codex_model(data.get("codexModel", DEFAULT_CODEX_MODEL)),
        "codexReasoningEffort": normalize_codex_reasoning_effort(data.get("codexReasoningEffort", DEFAULT_CODEX_REASONING_EFFORT)),
        "discord": normalize_discord_settings(data.get("discord")),
        "titleFontFamily": normalize_title_font_family(data.get("titleFontFamily", DEFAULT_TITLE_FONT_FAMILY)),
        "titleFontScale": clamp_title_font_scale(data.get("titleFontScale", DEFAULT_TITLE_FONT_SCALE)),
        "titleOutlineEnabled": bool(data.get("titleOutlineEnabled", False)),
        "titleOutlineColor": normalize_hex_color(data.get("titleOutlineColor", "#ffffff"), "#ffffff"),
        "titleOutlineWidth": clamp_title_outline_width(data.get("titleOutlineWidth", DEFAULT_TITLE_OUTLINE_WIDTH)),
        "titleShadowEnabled": bool(data.get("titleShadowEnabled", True)),
        "titleShadowColor": normalize_hex_color(data.get("titleShadowColor", "#ffffff"), "#ffffff"),
        "titleShadowBlur": clamp_title_shadow_blur(data.get("titleShadowBlur", DEFAULT_TITLE_SHADOW_BLUR)),
        "titleShadowX": clamp_title_shadow_offset(data.get("titleShadowX", 0.0), 0.0),
        "titleShadowY": clamp_title_shadow_offset(data.get("titleShadowY", 1.0), 1.0),
        "arrangeSpacing": clamp_arrange_spacing(data.get("arrangeSpacing", DEFAULT_ARRANGE_SPACING)),
        "arrangeSize": clamp_arrange_size(data.get("arrangeSize", DEFAULT_ARRANGE_SIZE)),
        "arrangeResizeParents": bool(data.get("arrangeResizeParents", True)),
        "arrangeRecursive": bool(data.get("arrangeRecursive", True)),
        "arrangeChildSpacing": clamp_arrange_spacing(data.get("arrangeChildSpacing", data.get("arrangeSpacing", DEFAULT_ARRANGE_SPACING))),
        "arrangeChildSize": clamp_arrange_size(data.get("arrangeChildSize", data.get("arrangeSize", DEFAULT_ARRANGE_SIZE))),
        "arrangeNestedChildSize": clamp_arrange_size(data.get("arrangeNestedChildSize", data.get("arrangeSize", DEFAULT_ARRANGE_SIZE))),
        "arrangeWorldParentSpacing": clamp_arrange_spacing(data.get("arrangeWorldParentSpacing", data.get("arrangeSpacing", DEFAULT_ARRANGE_SPACING))),
        "arrangeWorldParentSize": clamp_arrange_size(data.get("arrangeWorldParentSize", data.get("arrangeSize", DEFAULT_ARRANGE_SIZE))),
        "nestedLayerScale": clamp_nested_layer_scale(data.get("nestedLayerScale", 0.5)),
        "restartVisibleConsole": bool(data.get("restartVisibleConsole", False)),
        "consoleLogLevels": normalize_console_log_levels(data.get("consoleLogLevels")),
    }


def save_app_settings(settings: dict[str, Any]) -> None:
    SETTING_ROOT.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def current_sound_root() -> Path:
    return ensure_sound_root(Path(load_app_settings()["soundRoot"]))


def list_sound_files(sound_root: Path) -> list[dict[str, str]]:
    return [
        {"name": path.name, "url": f"/api/settings/sounds/{path.name}"}
        for path in sorted(sound_root.iterdir(), key=lambda item: item.name.lower())
        if path.is_file() and path.suffix.lower() in SOUND_EXTENSIONS
    ]


def setting_payload() -> dict[str, Any]:
    settings = load_app_settings()
    sound_root = ensure_sound_root(Path(settings["soundRoot"]))
    sounds = list_sound_files(sound_root)
    if settings["conversationSound"] and not any(sound["name"] == settings["conversationSound"] for sound in sounds):
        settings["conversationSound"] = ""
        save_app_settings(settings)
    if settings["inputSound"] and not any(sound["name"] == settings["inputSound"] for sound in sounds):
        settings["inputSound"] = ""
        save_app_settings(settings)
    return {
        "soundRoot": settings["soundRoot"],
        "defaultSoundRoot": str(DEFAULT_SOUND_ROOT.resolve()),
        "conversationSound": settings["conversationSound"],
        "conversationSoundVolume": settings["conversationSoundVolume"],
        "inputSound": settings["inputSound"],
        "inputSoundVolume": settings["inputSoundVolume"],
        "autoSummaryEnabled": settings["autoSummaryEnabled"],
        "autoSummaryTurns": settings["autoSummaryTurns"],
        "codexSandbox": settings["codexSandbox"],
        "codexModel": settings["codexModel"],
        "codexReasoningEffort": settings["codexReasoningEffort"],
        "discord": settings["discord"],
        "discordStatus": ABC_DISCORD_BRIDGE.status() if ABC_DISCORD_BRIDGE is not None else {},
        "titleFontFamily": settings["titleFontFamily"],
        "titleFontScale": settings["titleFontScale"],
        "titleOutlineEnabled": settings["titleOutlineEnabled"],
        "titleOutlineColor": settings["titleOutlineColor"],
        "titleOutlineWidth": settings["titleOutlineWidth"],
        "titleShadowEnabled": settings["titleShadowEnabled"],
        "titleShadowColor": settings["titleShadowColor"],
        "titleShadowBlur": settings["titleShadowBlur"],
        "titleShadowX": settings["titleShadowX"],
        "titleShadowY": settings["titleShadowY"],
        "arrangeSpacing": settings["arrangeSpacing"],
        "arrangeSize": settings["arrangeSize"],
        "arrangeResizeParents": settings["arrangeResizeParents"],
        "arrangeRecursive": settings["arrangeRecursive"],
        "arrangeChildSpacing": settings["arrangeChildSpacing"],
        "arrangeChildSize": settings["arrangeChildSize"],
        "arrangeNestedChildSize": settings["arrangeNestedChildSize"],
        "arrangeWorldParentSpacing": settings["arrangeWorldParentSpacing"],
        "arrangeWorldParentSize": settings["arrangeWorldParentSize"],
        "nestedLayerScale": settings["nestedLayerScale"],
        "restartVisibleConsole": settings["restartVisibleConsole"],
        "consoleLogLevels": settings["consoleLogLevels"],
        "sounds": sounds,
    }


def random_powan_style() -> dict[str, Any]:
    pair = random.choice(POWAN_COLOR_PALETTE)
    return {
        "shape": "cloud",
        "color": pair["color"],
        "accent": pair["accent"],
        "glow": True,
        "blur": True,
        "motion": "soft",
    }


def default_powan_style() -> dict[str, Any]:
    return {
        "shape": "cloud",
        "color": "#ffffff",
        "accent": "#8ddcff",
        "glow": True,
        "blur": True,
        "motion": "soft",
    }


def blank_document(random_color: bool = False) -> dict[str, Any]:
    return {
        "version": 1,
        "canvas": {
            "background": "#e8f8ff",
            "workspace": {
                "version": 1,
                "width": WORKSPACE_SIZE,
                "height": WORKSPACE_SIZE,
                "origin": {
                    "x": WORKSPACE_ORIGIN_X,
                    "y": WORKSPACE_ORIGIN_Y,
                },
            },
        },
        "nodes": [
            {
                "id": f"node-{uuid4().hex[:10]}",
                "title": "",
                "body": "",
                "code": "",
                "parent": None,
                "children": [],
                "style": random_powan_style() if random_color else default_powan_style(),
                "layout": {
                    "x": WORKSPACE_ORIGIN_X - DEFAULT_NODE_WIDTH // 2,
                    "y": WORKSPACE_ORIGIN_Y - DEFAULT_NODE_HEIGHT // 2,
                    "width": DEFAULT_NODE_WIDTH,
                    "height": DEFAULT_NODE_HEIGHT,
                },
            }
        ],
    }


def ensure_project(project: str) -> Path:
    return STORE.ensure_project(project)


STORE = PowanStore(POWAN_WORK_ROOT, DEFAULT_FILE, blank_document, log_server_event)
STORE.recover_interrupted_work(reason="server-startup")
CODEX_BRIDGE = CodexPowanBridge(log_server_event)
ABC_DISCORD_BRIDGE: AbcDiscordBridge | None = None


app.include_router(create_ai_router(STORE, DEFAULT_FILE, log_server_event))


@app.get("/")
def index() -> FileResponse:
    return no_cache_file(STATIC_ROOT / "project.html")


@app.get("/canvas")
def canvas() -> FileResponse:
    return no_cache_file(STATIC_ROOT / "index.html")


@app.get("/settings")
def settings_page() -> FileResponse:
    return no_cache_file(STATIC_ROOT / "settings.html")


@app.get("/api/projects")
def list_projects() -> dict[str, list[dict[str, str]]]:
    projects = [
        {
            "name": path.name,
            "path": str(path),
        }
        for path in sorted(POWAN_WORK_ROOT.iterdir(), key=lambda item: item.name)
        if path.is_dir()
    ]
    return {"projects": projects}


@app.post("/api/projects")
def create_project(request: ProjectCreateRequest) -> dict[str, str]:
    name = STORE.safe_project_name(request.name)
    root = ensure_project(name)
    return {
        "name": name,
        "root": str(root),
        "file": DEFAULT_FILE,
    }


@app.post("/api/projects/open")
def open_project_root(request: ProjectCreateRequest) -> dict[str, str]:
    name = STORE.safe_project_name(request.name)
    root = ensure_project(name)
    subprocess.Popen(["explorer", str(root)])
    return {
        "status": "opened",
        "name": name,
        "root": str(root),
    }


@app.get("/api/files")
def list_files(project: str) -> dict[str, list[str]]:
    return {"files": STORE.list_documents(project)}


@app.get("/api/settings")
def get_settings() -> dict[str, Any]:
    return setting_payload()


@app.post("/api/settings/sound-folder")
def save_sound_folder(request: SoundFolderRequest) -> dict[str, Any]:
    settings = load_app_settings()
    sound_root = ensure_sound_root(resolve_sound_root(request.soundRoot))
    sounds = list_sound_files(sound_root)
    settings["soundRoot"] = str(sound_root)
    if settings["conversationSound"] and not any(sound["name"] == settings["conversationSound"] for sound in sounds):
        settings["conversationSound"] = ""
    if settings["inputSound"] and not any(sound["name"] == settings["inputSound"] for sound in sounds):
        settings["inputSound"] = ""
    save_app_settings(settings)
    log_server_event("info", "sound-folder-updated", {"soundRoot": settings["soundRoot"]})
    return setting_payload()


@app.post("/api/settings/sound-folder/pick")
def pick_sound_folder() -> dict[str, Any]:
    settings = load_app_settings()
    selected = pick_sound_folder_with_explorer(Path(settings["soundRoot"]))
    if selected is None:
        log_server_event("info", "sound-folder-pick-cancelled", {"soundRoot": settings["soundRoot"]})
        payload = setting_payload()
        payload["cancelled"] = True
        return payload
    sound_root = ensure_sound_root(selected)
    sounds = list_sound_files(sound_root)
    settings["soundRoot"] = str(sound_root)
    if settings["conversationSound"] and not any(sound["name"] == settings["conversationSound"] for sound in sounds):
        settings["conversationSound"] = ""
    if settings["inputSound"] and not any(sound["name"] == settings["inputSound"] for sound in sounds):
        settings["inputSound"] = ""
    save_app_settings(settings)
    log_server_event("info", "sound-folder-picked", {"soundRoot": settings["soundRoot"]})
    payload = setting_payload()
    payload["cancelled"] = False
    return payload


@app.post("/api/settings/conversation-sound")
def save_conversation_sound(request: ConversationSoundRequest) -> dict[str, Any]:
    settings = load_app_settings()
    sound_root = ensure_sound_root(Path(settings["soundRoot"]))
    sound_name = request.conversationSound.strip()
    if sound_name:
        safe_name = safe_sound_name(sound_name)
        path = (sound_root / safe_name).resolve()
        if sound_root.resolve() not in path.parents or not path.exists() or not path.is_file():
            raise HTTPException(status_code=400, detail="Sound file not found")
        sound_name = safe_name
    settings["conversationSound"] = sound_name
    save_app_settings(settings)
    log_server_event("info", "conversation-sound-updated", {"conversationSound": sound_name})
    return setting_payload()


@app.post("/api/settings/conversation-sound-volume")
def save_conversation_sound_volume(request: ConversationSoundVolumeRequest) -> dict[str, Any]:
    settings = load_app_settings()
    settings["conversationSoundVolume"] = clamp_sound_volume(request.conversationSoundVolume)
    save_app_settings(settings)
    log_server_event("info", "conversation-sound-volume-updated", {"volume": settings["conversationSoundVolume"]})
    return setting_payload()


@app.post("/api/settings/input-sound")
def save_input_sound(request: InputSoundRequest) -> dict[str, Any]:
    settings = load_app_settings()
    sound_root = ensure_sound_root(Path(settings["soundRoot"]))
    sound_name = request.inputSound.strip()
    if sound_name:
        safe_name = safe_sound_name(sound_name)
        path = (sound_root / safe_name).resolve()
        if sound_root.resolve() not in path.parents or not path.exists() or not path.is_file():
            raise HTTPException(status_code=400, detail="Sound file not found")
        sound_name = safe_name
    settings["inputSound"] = sound_name
    save_app_settings(settings)
    log_server_event("info", "input-sound-updated", {"inputSound": sound_name})
    return setting_payload()


@app.post("/api/settings/input-sound-volume")
def save_input_sound_volume(request: InputSoundVolumeRequest) -> dict[str, Any]:
    settings = load_app_settings()
    settings["inputSoundVolume"] = clamp_sound_volume(request.inputSoundVolume)
    save_app_settings(settings)
    log_server_event("info", "input-sound-volume-updated", {"volume": settings["inputSoundVolume"]})
    return setting_payload()


@app.post("/api/settings/conversation-auto-summary")
def save_conversation_auto_summary(request: ConversationAutoSummaryRequest) -> dict[str, Any]:
    settings = load_app_settings()
    settings["autoSummaryEnabled"] = bool(request.enabled)
    settings["autoSummaryTurns"] = clamp_auto_summary_turns(request.turns)
    save_app_settings(settings)
    log_server_event(
        "info",
        "conversation-auto-summary-updated",
        {
            "enabled": settings["autoSummaryEnabled"],
            "turns": settings["autoSummaryTurns"],
        },
    )
    return setting_payload()


@app.post("/api/settings/codex-sandbox")
def save_codex_sandbox(request: CodexSandboxRequest) -> dict[str, Any]:
    settings = load_app_settings()
    settings["codexSandbox"] = normalize_codex_sandbox(request.codexSandbox)
    save_app_settings(settings)
    log_server_event("info", "codex-sandbox-updated", {"codexSandbox": settings["codexSandbox"]})
    return setting_payload()


@app.post("/api/settings/codex-model")
def save_codex_model_settings(request: CodexModelSettingsRequest) -> dict[str, Any]:
    settings = load_app_settings()
    settings["codexModel"] = normalize_codex_model(request.codexModel)
    settings["codexReasoningEffort"] = normalize_codex_reasoning_effort(request.codexReasoningEffort)
    save_app_settings(settings)
    log_server_event(
        "info",
        "codex-model-settings-updated",
        {
            "codexModel": settings["codexModel"],
            "codexReasoningEffort": settings["codexReasoningEffort"],
        },
    )
    return setting_payload()


@app.post("/api/settings/discord")
def save_discord_settings(request: DiscordSettingsRequest) -> dict[str, Any]:
    settings = load_app_settings()
    settings["discord"] = normalize_discord_settings(base_model_payload(request))
    save_app_settings(settings)
    bridge_status = ABC_DISCORD_BRIDGE.apply_settings(settings) if ABC_DISCORD_BRIDGE is not None else {}
    log_server_event(
        "info",
        "discord-settings-updated",
        {
            "enabled": settings["discord"]["enabled"],
            "channelId": settings["discord"]["channelId"],
            "project": settings["discord"]["project"],
            "file": settings["discord"]["file"],
            "targetNodeId": settings["discord"]["targetNodeId"],
            "bridgeStatus": bridge_status,
        },
    )
    return setting_payload()


@app.get("/api/settings/discord/status")
def get_discord_status() -> dict[str, Any]:
    return ABC_DISCORD_BRIDGE.status() if ABC_DISCORD_BRIDGE is not None else {"running": False, "status": "unavailable"}


@app.post("/api/settings/title-style")
def save_title_style_settings(request: TitleStyleSettingsRequest) -> dict[str, Any]:
    settings = load_app_settings()
    settings["titleFontFamily"] = normalize_title_font_family(request.titleFontFamily)
    settings["titleFontScale"] = clamp_title_font_scale(request.titleFontScale)
    settings["titleOutlineEnabled"] = bool(request.titleOutlineEnabled)
    settings["titleOutlineColor"] = normalize_hex_color(request.titleOutlineColor, "#ffffff")
    settings["titleOutlineWidth"] = clamp_title_outline_width(request.titleOutlineWidth)
    settings["titleShadowEnabled"] = bool(request.titleShadowEnabled)
    settings["titleShadowColor"] = normalize_hex_color(request.titleShadowColor, "#ffffff")
    settings["titleShadowBlur"] = clamp_title_shadow_blur(request.titleShadowBlur)
    settings["titleShadowX"] = clamp_title_shadow_offset(request.titleShadowX, 0.0)
    settings["titleShadowY"] = clamp_title_shadow_offset(request.titleShadowY, 1.0)
    save_app_settings(settings)
    log_server_event(
        "info",
        "title-style-settings-updated",
        {
            "font": settings["titleFontFamily"],
            "scale": settings["titleFontScale"],
            "outline": settings["titleOutlineEnabled"],
            "shadow": settings["titleShadowEnabled"],
        },
    )
    return setting_payload()


@app.post("/api/settings/arrange")
def save_arrange_settings(request: ArrangeSettingsRequest) -> dict[str, Any]:
    settings = load_app_settings()
    settings["arrangeSpacing"] = clamp_arrange_spacing(request.arrangeSpacing)
    settings["arrangeSize"] = clamp_arrange_size(request.arrangeSize)
    settings["arrangeResizeParents"] = bool(request.arrangeResizeParents)
    settings["arrangeRecursive"] = bool(request.arrangeRecursive)
    settings["arrangeChildSpacing"] = clamp_arrange_spacing(request.arrangeChildSpacing if request.arrangeChildSpacing is not None else request.arrangeSpacing)
    settings["arrangeChildSize"] = clamp_arrange_size(request.arrangeChildSize if request.arrangeChildSize is not None else request.arrangeSize)
    settings["arrangeNestedChildSize"] = clamp_arrange_size(request.arrangeNestedChildSize if request.arrangeNestedChildSize is not None else request.arrangeSize)
    settings["arrangeWorldParentSpacing"] = clamp_arrange_spacing(
        request.arrangeWorldParentSpacing if request.arrangeWorldParentSpacing is not None else request.arrangeSpacing
    )
    settings["arrangeWorldParentSize"] = clamp_arrange_size(request.arrangeWorldParentSize if request.arrangeWorldParentSize is not None else request.arrangeSize)
    settings["nestedLayerScale"] = clamp_nested_layer_scale(request.nestedLayerScale if request.nestedLayerScale is not None else 0.5)
    save_app_settings(settings)
    log_server_event(
        "info",
        "arrange-settings-updated",
        {
            "resizeParents": settings["arrangeResizeParents"],
            "recursive": settings["arrangeRecursive"],
            "childSpacing": settings["arrangeChildSpacing"],
            "childSize": settings["arrangeChildSize"],
            "nestedSize": settings["arrangeNestedChildSize"],
            "worldSpacing": settings["arrangeWorldParentSpacing"],
            "worldSize": settings["arrangeWorldParentSize"],
            "nestedLayerScale": settings["nestedLayerScale"],
        },
    )
    return setting_payload()


@app.post("/api/settings/console-log-levels")
def save_console_log_levels(request: ConsoleLogSettingsRequest) -> dict[str, Any]:
    settings = load_app_settings()
    settings["consoleLogLevels"] = normalize_console_log_levels(request.consoleLogLevels)
    save_app_settings(settings)
    levels = ",".join(settings["consoleLogLevels"])
    log_server_event(
        "info",
        "console-log-levels-updated",
        {
            "message": f"console log levels updated: {levels}",
            "consoleLogLevels": settings["consoleLogLevels"],
            "console": True,
        },
    )
    return setting_payload()


@app.post("/api/settings/restart-visible-console")
def save_restart_visible_console(request: RestartVisibleConsoleSettingsRequest) -> dict[str, Any]:
    settings = load_app_settings()
    settings["restartVisibleConsole"] = bool(request.restartVisibleConsole)
    save_app_settings(settings)
    log_server_event("info", "restart-visible-console-updated", {"restartVisibleConsole": settings["restartVisibleConsole"]})
    return setting_payload()


@app.get("/api/settings/sounds")
def list_sounds() -> dict[str, list[dict[str, str]]]:
    return {"sounds": list_sound_files(current_sound_root())}


@app.get("/api/settings/sounds/{name}")
def get_sound(name: str) -> FileResponse:
    safe_name = safe_sound_name(name)
    sound_root = current_sound_root()
    path = (sound_root / safe_name).resolve()
    if sound_root.resolve() not in path.parents or not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Sound file not found")
    return FileResponse(path)


@app.get("/api/doc/{name}")
def load_doc(name: str, project: str) -> dict[str, Any]:
    data = STORE.load_document(project, name)
    return AbcDocument.model_validate(data).model_dump()


@app.post("/api/doc/{name}")
def save_doc(
    name: str,
    document: AbcDocument,
    project: str,
    x_abc_document_snapshot: str | None = Header(default=None),
) -> dict[str, str]:
    document_name = STORE.safe_powan_name(name)
    client_snapshot = unquote(x_abc_document_snapshot) if x_abc_document_snapshot is not None else None
    try:
        current_document = STORE.load_document(project, document_name)
    except HTTPException as exc:
        if exc.status_code != 404:
            raise
        current_document = None
    if current_document is not None and not client_snapshot:
        log_server_event(
            "warn",
            "save-document-missing-snapshot-rejected",
            {
                "message": f"save rejected: missing snapshot {document_name}",
                "project": STORE.safe_project_name(project),
                "file": document_name,
                "clientNodes": len(document.nodes),
                "serverNodes": len(current_document.get("nodes") or []),
                "console": True,
            },
        )
        raise HTTPException(status_code=428, detail="Document snapshot is required")
    if current_document is not None:
        current_snapshot = document_signature(current_document)
        if current_snapshot != client_snapshot:
            log_server_event(
                "warn",
                "save-document-stale-rejected",
                {
                    "message": f"save rejected: stale snapshot {document_name}",
                    "project": STORE.safe_project_name(project),
                    "file": document_name,
                    "clientNodes": len(document.nodes),
                    "serverNodes": len(current_document.get("nodes") or []),
                    "console": True,
                },
            )
            raise HTTPException(status_code=409, detail="Document changed on server")
    payload = document.model_dump()
    STORE.save_document(project, document_name, payload, write_export=True)
    log_server_event(
        "info",
        "save-document-persist-complete",
        {
            "message": f"document persisted: {document_name}, {len(payload.get('nodes') or [])} nodes",
            "project": STORE.safe_project_name(project),
            "file": document_name,
            "nodeCount": len(payload.get("nodes") or []),
            "console": True,
        },
    )
    return {
        "status": "saved",
        "project": STORE.safe_project_name(project),
        "file": document_name,
        "snapshot": document_signature(payload),
    }


@app.post("/api/doc")
def create_doc(project: str, random_color: bool = False) -> dict[str, str]:
    ensure_project(project)
    name = f"canvas-{uuid4().hex[:8]}.powan"
    STORE.save_document(project, name, blank_document(random_color=random_color), write_export=True)
    return {"project": STORE.safe_project_name(project), "file": name}


def ensure_powan_exists(project: str, file: str, node_id: str) -> None:
    document = STORE.load_document(project, file)
    if not any(str(node.get("id")) == node_id for node in document.get("nodes") or []):
        raise HTTPException(status_code=404, detail="Powan not found")


def mark_codex_disconnected_safe(
    project: str,
    file: str,
    node_id: str,
    conversation_id: int | None,
    reason: str,
) -> None:
    try:
        STORE.mark_powan_codex_disconnected(
            project,
            file,
            node_id,
            conversation_id=conversation_id,
            reason=reason,
        )
    except Exception as exc:
        log_server_event(
            "error",
            "codex-disconnected-mark-failed",
            {
                "project": STORE.safe_project_name(project),
                "file": STORE.safe_powan_name(file),
                "nodeId": node_id,
                "conversationId": conversation_id,
                "reason": reason,
                "error": repr(exc),
            },
        )


DEAD_CODEX_RUN_ERROR = "Codexプロセスが見つかりません。DBの作業中状態だけが残っていたため失敗にしました。"


def find_codex_pid_for_thread(thread_id: str) -> int | None:
    clean_thread_id = str(thread_id or "").strip()
    if not clean_thread_id or os.name != "nt":
        return None
    escaped_thread_id = clean_thread_id.replace("'", "''")
    command = (
        "$thread = '" + escaped_thread_id + "'; "
        "$matches = Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -like \"*$thread*\" -and "
        "($_.Name -ieq 'codex.exe' -or $_.Name -ieq 'node.exe' -or $_.Name -ieq 'cmd.exe') }; "
        "$preferred = $matches | Where-Object { $_.Name -ieq 'codex.exe' } | Select-Object -First 1; "
        "if (-not $preferred) { $preferred = $matches | Select-Object -First 1 }; "
        "if ($preferred) { $preferred.ProcessId }"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=4,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    for line in (result.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            return int(line)
        except ValueError:
            continue
    return None


def reconcile_running_agent_runs(
    project: str,
    file: str,
    *,
    node_id: str | None = None,
    conversation_id: int | None = None,
) -> list[dict[str, Any]]:
    safe_project = STORE.safe_project_name(project)
    safe_file = STORE.safe_powan_name(file)
    live_runs: list[dict[str, Any]] = []
    for run in STORE.list_running_agent_runs(project, file):
        run_node_id = str(run.get("powanId") or "")
        run_conversation_id = run.get("conversationId")
        if node_id and run_node_id != node_id:
            continue
        if conversation_id is not None and int(run_conversation_id or 0) != int(conversation_id):
            continue
        live_info = CODEX_BRIDGE.active_run_info(
            project=safe_project,
            document_name=safe_file,
            node_id=run_node_id,
            run_id=int(run["id"]),
        )
        if live_info is not None:
            next_run = {**run, "live": True}
            if live_info.get("pid") is not None:
                next_run["pid"] = live_info["pid"]
            next_run["processRunning"] = bool(live_info.get("processRunning"))
            live_runs.append(next_run)
            continue
        pid = run.get("pid")
        if pid is None:
            pid = find_codex_pid_for_thread(str(run.get("threadId") or ""))
            if pid is not None:
                STORE.set_agent_run_pid(project, int(run["id"]), int(pid))
        if pid is not None and CODEX_BRIDGE.is_pid_running(int(pid)):
            live_runs.append({**run, "pid": int(pid), "live": True, "processRunning": True})
            continue
        failed = STORE.fail_agent_run_if_running(project, int(run["id"]), DEAD_CODEX_RUN_ERROR)
        if failed is None:
            continue
        STORE.fail_child_command_dispatches_for_run(
            project,
            str(failed.get("documentName") or safe_file),
            str(failed.get("powanId") or run_node_id),
            int(failed["conversationId"]) if failed.get("conversationId") is not None else None,
            DEAD_CODEX_RUN_ERROR,
        )
        mark_codex_disconnected_safe(
            project,
            str(failed.get("documentName") or safe_file),
            str(failed.get("powanId") or run_node_id),
            int(failed["conversationId"]) if failed.get("conversationId") is not None else None,
            "codex-process-missing",
        )
        log_server_event(
            "warn",
            "codex-run-reconciled-dead",
            {
                "project": safe_project,
                "file": safe_file,
                "nodeId": failed.get("powanId") or run_node_id,
                "conversationId": failed.get("conversationId"),
                "runId": failed.get("id"),
            },
        )
    return live_runs


def live_conversation_payload(project: str, file: str, node_id: str, conversation_id: int | None = None) -> dict[str, Any]:
    if conversation_id is None:
        payload = STORE.list_conversation_messages(project, file, node_id)
    else:
        payload = STORE.conversation_messages_by_id(project, file, node_id, conversation_id)
    resolved_conversation_id = int(payload["conversationId"])
    live_runs = reconcile_running_agent_runs(
        project,
        file,
        node_id=node_id,
        conversation_id=resolved_conversation_id,
    )
    payload = STORE.conversation_messages_by_id(project, file, node_id, resolved_conversation_id)
    payload["activeRun"] = live_runs[0] if live_runs else None
    return payload


def powan_label_from_document(document: dict[str, Any], node_id: str | None) -> str:
    if not node_id:
        return "ユーザー"
    for node in document.get("nodes") or []:
        if isinstance(node, dict) and str(node.get("id") or "") == str(node_id):
            return str(node.get("title") or node.get("body") or "名前のないポワン").strip() or "名前のないポワン"
    return "名前のないポワン"


def powan_work_message(status: str, sender_label: str, receiver_label: str, source: str) -> str:
    status_labels = {
        "received": "受信",
        "working": "作業中",
        "completed": "完了",
        "failed": "失敗",
        "cancelled": "キャンセル",
    }
    return f"{sender_label} -> {receiver_label} / {status_labels.get(status, status)}"


def limit_prompt_text(text: Any, limit: int = 12000) -> str:
    value = str(text or "")
    if limit <= 0:
        return ""
    if len(value) <= limit:
        return value
    return f"{value[:limit]}\n... truncated {len(value) - limit} chars ..."


def incoming_kind_for_source(source: str) -> str:
    if source == "command-children":
        return "parent_command"
    if source == "command-child-return":
        return "child_replies"
    return "operator_message"


def incoming_allowed_action(source: str, *, continue_after_child_replies: bool = False) -> str:
    if source == "command-child-return" and not continue_after_child_replies:
        return "read_only"
    return "may_command_children"


def incoming_from_payload(source: str, sender_node_id: str | None, sender_label: str) -> dict[str, Any]:
    if source == "command-children":
        return {
            "kind": "parent_powan",
            "id": sender_node_id,
            "name": sender_label,
        }
    if source == "command-child-return":
        return {
            "kind": "child_powan_bundle",
            "id": sender_node_id,
            "name": sender_label,
        }
    return {
        "kind": "operator",
        "id": None,
        "name": "ユーザー",
    }


def incoming_system_instruction(kind: str, allowed_action: str) -> str:
    if kind == "parent_command":
        return "これは親ポワンからこのポワンへの命令です。from.kind と parentCommand を見て処理してください。"
    if kind == "child_replies":
        if allowed_action == "may_command_children":
            return "これは子ポワンから親ポワンへ戻った返答通知です。commandChildren.continueAfterChildReplies=true により、必要なら子返答後も command-children を続けて実行できます。"
        return "これは子ポワンから親ポワンへ戻った返答通知です。allowedAction=read_only の範囲で、返答内容の確認と要約だけを行ってください。"
    return "これはユーザーからこのポワンへの入力です。"


def build_incoming_message_payload(
    *,
    source: str,
    text: str,
    sender_node_id: str | None,
    sender_label: str,
    receiver_node_id: str,
    receiver_label: str,
    conversation_id: int,
    user_message_id: int | None,
    continue_after_child_replies: bool = False,
    command_children_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    kind = incoming_kind_for_source(source)
    allowed_action = incoming_allowed_action(
        source,
        continue_after_child_replies=continue_after_child_replies,
    )
    payload: dict[str, Any] = {
        "kind": kind,
        "source": source,
        "from": incoming_from_payload(source, sender_node_id, sender_label),
        "to": {
            "kind": "powan",
            "id": receiver_node_id,
            "name": receiver_label,
            "conversationId": conversation_id,
            "messageId": user_message_id,
        },
        "operatorMessage": "",
        "parentCommand": "",
        "childReplies": [],
        "body": text,
        "allowedAction": allowed_action,
        "systemInstruction": incoming_system_instruction(kind, allowed_action),
    }
    if command_children_context is not None:
        payload["commandChildren"] = {
            **command_children_context,
            "continueAfterChildReplies": bool(continue_after_child_replies),
        }
    if kind == "parent_command":
        payload["parentCommand"] = text
    elif kind == "child_replies":
        payload["childReplies"] = []
    else:
        payload["operatorMessage"] = text
    return payload


def child_reply_payloads(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    replies: list[dict[str, Any]] = []
    for result in results:
        assistant_message = result.get("assistantMessage") if isinstance(result.get("assistantMessage"), dict) else None
        agent_run = result.get("agentRun") if isinstance(result.get("agentRun"), dict) else None
        replies.append(
            {
                "from": {
                    "kind": "child_powan",
                    "id": result.get("nodeId"),
                    "name": str(result.get("meaning") or "名前のないポワン"),
                },
                "status": str(result.get("status") or "unknown"),
                "conversationId": result.get("conversationId"),
                "dispatchSessionId": result.get("dispatchSessionId"),
                "dispatchId": result.get("dispatchId"),
                "assistantMessageId": assistant_message.get("id") if assistant_message else None,
                "agentRunId": agent_run.get("id") if agent_run else None,
                "text": limit_prompt_text((assistant_message or {}).get("text") or "", 12000),
                "error": limit_prompt_text(result.get("error") or "", 4000),
            }
        )
    return replies


def child_return_incoming_message(
    *,
    parent_id: str,
    parent_label: str,
    parent_conversation_id: int,
    parent_message_id: int | None,
    parent_text: str,
    results: list[dict[str, Any]],
    continue_after_child_replies: bool = False,
    dispatch_session_id: str = "",
) -> dict[str, Any]:
    payload = build_incoming_message_payload(
        source="command-child-return",
        text=parent_text,
        sender_node_id=str(results[0].get("nodeId") or "") if len(results) == 1 else None,
        sender_label="子ポワン一括返答",
        receiver_node_id=parent_id,
        receiver_label=parent_label,
        conversation_id=parent_conversation_id,
        user_message_id=parent_message_id,
        continue_after_child_replies=continue_after_child_replies,
        command_children_context={
            "dispatchSessionId": dispatch_session_id,
        },
    )
    payload["childReplies"] = child_reply_payloads(results)
    return payload


def remember_powan_work_event(details: dict[str, Any]) -> dict[str, Any]:
    global POWAN_WORK_EVENT_SEQUENCE
    with POWAN_WORK_EVENT_LOCK:
        POWAN_WORK_EVENT_SEQUENCE += 1
        event = {
            "sequence": POWAN_WORK_EVENT_SEQUENCE,
            "time": datetime.now().isoformat(timespec="milliseconds"),
            **details,
        }
        POWAN_WORK_EVENTS.append(event)
        del POWAN_WORK_EVENTS[:-POWAN_WORK_EVENT_LIMIT]
        return event


def log_powan_work_status(
    status: str,
    *,
    project: str,
    file: str,
    source: str,
    receiver_id: str,
    receiver_label: str,
    sender_id: str | None = None,
    sender_label: str = "ユーザー",
    conversation_id: int | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    details: dict[str, Any] = {
        "console": True,
        "message": powan_work_message(status, sender_label, receiver_label, source),
        "project": STORE.safe_project_name(project),
        "file": STORE.safe_powan_name(file),
        "source": source,
        "status": status,
        "from": {
            "id": sender_id,
            "meaning": sender_label,
        },
        "to": {
            "id": receiver_id,
            "meaning": receiver_label,
        },
    }
    if conversation_id is not None:
        details["conversationId"] = conversation_id
    if extra:
        details.update(extra)
    remember_powan_work_event(details)
    log_server_event("info", f"powan-work-{status}", details)


def remember_powan_batch_work_event(
    *,
    status: str,
    message: str,
    project: str,
    file: str,
    source: str,
    sender_id: str,
    sender_label: str,
    receiver_label: str,
    count: int,
    instruction: str,
    extra: dict[str, Any] | None = None,
) -> None:
    details: dict[str, Any] = {
        "console": True,
        "message": message,
        "project": STORE.safe_project_name(project),
        "file": STORE.safe_powan_name(file),
        "source": source,
        "status": status,
        "from": {
            "id": sender_id,
            "meaning": sender_label,
        },
        "to": {
            "id": None,
            "meaning": receiver_label,
        },
        "count": count,
        "instructionPreview": compact_console_text(instruction),
    }
    if extra:
        details.update(extra)
    remember_powan_work_event(details)


def run_powan_codex_message(
    node_id: str,
    *,
    project: str,
    file: str,
    text: str,
    include_meaning_tree: bool = False,
    include_direct_child_code: bool = False,
    attachments: list[dict[str, Any]] | None = None,
    source: str = "conversation",
    sender_node_id: str | None = None,
    sender_label_override: str | None = None,
    pre_appended_user_message: dict[str, Any] | None = None,
    incoming_message: dict[str, Any] | None = None,
) -> dict[str, Any]:
    document = STORE.load_document(project, file)
    if not any(str(node.get("id")) == node_id for node in document.get("nodes") or []):
        raise HTTPException(status_code=404, detail="Powan not found")
    receiver_label = powan_label_from_document(document, node_id)
    sender_label = (
        sender_label_override
        or (powan_label_from_document(document, sender_node_id) if sender_node_id else "ユーザー")
    )
    materialized_attachments = materialize_conversation_attachments(project, attachments or [])
    if pre_appended_user_message is not None:
        user_message = pre_appended_user_message
        conversation_id = int(user_message.get("conversationId") or 0)
        if conversation_id <= 0:
            raise HTTPException(status_code=500, detail="Pre-appended user message is missing conversationId")
        conversation_payload = STORE.conversation_messages_by_id(project, file, node_id, conversation_id)
        conversation = conversation_payload["conversation"]
        messages = conversation_payload["messages"]
    else:
        conversation = STORE.active_conversation(project, file, node_id)
        log_powan_work_status(
            "received",
            project=project,
            file=file,
            source=source,
            sender_id=sender_node_id,
            sender_label=sender_label,
            receiver_id=node_id,
            receiver_label=receiver_label,
            conversation_id=conversation["id"],
            extra={
                "textPreview": compact_console_text(text),
                "messageLength": len(text.strip()),
                "includeMeaningTree": bool(include_meaning_tree),
                "includeDirectChildCode": bool(include_direct_child_code),
                "attachmentCount": len(materialized_attachments),
            },
        )
        user_message = STORE.append_conversation_message(
            project,
            file,
            node_id,
            "user",
            conversation_record_text(text, materialized_attachments),
        )
        log_server_event(
            "info",
            "powan-user-message-appended",
            {
                "project": STORE.safe_project_name(project),
                "file": STORE.safe_powan_name(file),
                "nodeId": node_id,
                "conversationId": conversation["id"],
                "messageId": user_message.get("id"),
                "source": source,
                "senderNodeId": sender_node_id,
                "messageLength": len(text.strip()),
            },
        )
        messages = STORE.list_conversation_messages(project, file, node_id)["messages"]
    incoming_message_payload = incoming_message or build_incoming_message_payload(
        source=source,
        text=text,
        sender_node_id=sender_node_id,
        sender_label=sender_label,
        receiver_node_id=node_id,
        receiver_label=receiver_label,
        conversation_id=int(conversation["id"]),
        user_message_id=int(user_message["id"]) if user_message.get("id") is not None else None,
    )
    project_root_path = STORE.project_root(project)
    settings = load_app_settings()
    codex_sandbox = normalize_codex_sandbox(settings.get("codexSandbox"))
    codex_model = normalize_codex_model(settings.get("codexModel"))
    codex_reasoning_effort = normalize_codex_reasoning_effort(settings.get("codexReasoningEffort"))
    log_server_event(
        "info",
        "codex-exec-start",
        {
            "project": STORE.safe_project_name(project),
            "file": STORE.safe_powan_name(file),
            "nodeId": node_id,
            "conversationId": conversation["id"],
            "source": source,
            "hasThread": bool(conversation.get("codexThreadId")),
            "messageLength": len(text.strip()),
            "includeMeaningTree": bool(include_meaning_tree),
            "includeDirectChildCode": bool(include_direct_child_code),
            "attachmentCount": len(materialized_attachments),
            "attachmentPathCount": sum(1 for attachment in materialized_attachments if isinstance(attachment, dict) and attachment.get("path")),
            "codexSandbox": codex_sandbox,
            "codexModel": codex_model,
            "codexReasoningEffort": codex_reasoning_effort,
        },
    )
    log_powan_work_status(
        "working",
        project=project,
        file=file,
        source=source,
        sender_id=sender_node_id,
        sender_label=sender_label,
        receiver_id=node_id,
        receiver_label=receiver_label,
        conversation_id=conversation["id"],
        extra={
            "textPreview": compact_console_text(text),
            "hasThread": bool(conversation.get("codexThreadId")),
            "codexSandbox": codex_sandbox,
            "codexModel": codex_model,
            "codexReasoningEffort": codex_reasoning_effort,
            "includeDirectChildCode": bool(include_direct_child_code),
        },
    )
    run_payload = {
        "project": STORE.safe_project_name(project),
        "file": STORE.safe_powan_name(file),
        "nodeId": node_id,
        "conversationId": conversation["id"],
        "threadId": conversation.get("codexThreadId"),
        "source": source,
        "userText": text,
        "includeMeaningTree": bool(include_meaning_tree),
        "includeDirectChildCode": bool(include_direct_child_code),
        "attachmentCount": len(materialized_attachments),
        "codexSandbox": codex_sandbox,
        "codexModel": codex_model,
        "codexReasoningEffort": codex_reasoning_effort,
        "incomingKind": incoming_message_payload.get("kind"),
        "incomingFrom": incoming_message_payload.get("from"),
        "allowedAction": incoming_message_payload.get("allowedAction"),
        "commandChildren": incoming_message_payload.get("commandChildren"),
    }
    agent_run = STORE.start_agent_run(project, conversation["id"], node_id, run_payload)
    try:
        result = CODEX_BRIDGE.run(
            project_root=project_root_path,
            project=STORE.safe_project_name(project),
            document_name=STORE.safe_powan_name(file),
            document=document,
            node_id=node_id,
            user_text=text,
            conversation=conversation,
            messages=messages,
            incoming_message=incoming_message_payload,
            include_meaning_tree=bool(include_meaning_tree),
            include_direct_child_code=bool(include_direct_child_code),
            attachments=materialized_attachments,
            codex_sandbox=codex_sandbox,
            codex_model=codex_model,
            codex_reasoning_effort=codex_reasoning_effort,
            agent_run_id=int(agent_run["id"]),
            on_process_started=lambda pid: STORE.set_agent_run_pid(project, int(agent_run["id"]), int(pid)),
        )
    except Exception as exc:
        detail = f"Codex exec crashed before returning: {exc}"
        log_powan_work_status(
            "failed",
            project=project,
            file=file,
            source=source,
            sender_id=sender_node_id,
            sender_label=sender_label,
            receiver_id=node_id,
            receiver_label=receiver_label,
            conversation_id=conversation["id"],
            extra={
                "textPreview": compact_console_text(text),
                "error": repr(exc),
            },
        )
        log_server_event(
            "error",
            "codex-exec-crashed",
            {
                "project": STORE.safe_project_name(project),
                "file": STORE.safe_powan_name(file),
                "nodeId": node_id,
                "conversationId": conversation["id"],
                "source": source,
                "error": repr(exc),
            },
        )
        STORE.finish_agent_run(
            project,
            agent_run["id"],
            "failed",
            {
                **run_payload,
                "crashed": True,
            },
            error_text=detail,
        )
        mark_codex_disconnected_safe(project, file, node_id, int(conversation["id"]), "codex-exec-crashed")
        raise HTTPException(status_code=502, detail=detail) from exc
    if result.thread_id and result.thread_id != conversation.get("codexThreadId"):
        STORE.set_conversation_codex_thread_id(project, conversation["id"], result.thread_id)
    run_payload = {
        **run_payload,
        "threadId": result.thread_id,
        "resumed": result.resumed,
        "command": result.command,
        "durationMs": result.duration_ms,
    }
    if result.cancelled:
        agent_run = STORE.finish_agent_run(
            project,
            agent_run["id"],
            "cancelled",
            run_payload,
            output_text=result.text,
            error_text=result.stderr[-4000:],
        )
        log_server_event(
            "info",
            "codex-exec-cancelled",
            {
                "project": STORE.safe_project_name(project),
                "file": STORE.safe_powan_name(file),
                "nodeId": node_id,
                "conversationId": conversation["id"],
                "threadId": result.thread_id,
                "source": source,
                "durationMs": result.duration_ms,
            },
        )
        log_powan_work_status(
            "cancelled",
            project=project,
            file=file,
            source=source,
            sender_id=sender_node_id,
            sender_label=sender_label,
            receiver_id=node_id,
            receiver_label=receiver_label,
            conversation_id=conversation["id"],
            extra={
                "textPreview": compact_console_text(text),
                "threadId": result.thread_id,
                "durationMs": result.duration_ms,
            },
        )
        return {
            "conversationId": conversation["id"],
            "codexThreadId": result.thread_id,
            "cancelled": True,
            "userMessage": user_message,
            "assistantMessage": None,
            "agentRun": agent_run,
        }
    if result.returncode != 0 or not result.text:
        STORE.finish_agent_run(
            project,
            agent_run["id"],
            "failed",
            run_payload,
            output_text=result.text,
            error_text=result.stderr[-4000:],
        )
        log_server_event(
            "error",
            "codex-exec-failed",
            {
                "project": STORE.safe_project_name(project),
                "file": STORE.safe_powan_name(file),
                "nodeId": node_id,
                "conversationId": conversation["id"],
                "returncode": result.returncode,
                "source": source,
                "stderr": result.stderr[-1000:],
                "stdout": result.stdout[-1000:],
            },
        )
        log_powan_work_status(
            "failed",
            project=project,
            file=file,
            source=source,
            sender_id=sender_node_id,
            sender_label=sender_label,
            receiver_id=node_id,
            receiver_label=receiver_label,
            conversation_id=conversation["id"],
            extra={
                "textPreview": compact_console_text(text),
                "threadId": result.thread_id,
                "returncode": result.returncode,
                "durationMs": result.duration_ms,
            },
        )
        mark_codex_disconnected_safe(project, file, node_id, int(conversation["id"]), "codex-exec-failed")
        raise HTTPException(status_code=502, detail="Codex exec failed")
    assistant_message = STORE.append_conversation_message(project, file, node_id, "assistant", result.text)
    agent_run = STORE.finish_agent_run(
        project,
        agent_run["id"],
        "completed",
        run_payload,
        output_text=result.text,
        error_text=result.stderr[-4000:],
    )
    log_server_event(
        "info",
        "codex-exec-complete",
        {
            "project": STORE.safe_project_name(project),
            "file": STORE.safe_powan_name(file),
            "nodeId": node_id,
            "conversationId": conversation["id"],
            "threadId": result.thread_id,
            "resumed": result.resumed,
            "source": source,
            "durationMs": result.duration_ms,
            "outputLength": len(result.text),
        },
    )
    log_powan_work_status(
        "completed",
        project=project,
        file=file,
        source=source,
        sender_id=sender_node_id,
        sender_label=sender_label,
        receiver_id=node_id,
        receiver_label=receiver_label,
        conversation_id=conversation["id"],
        extra={
            "textPreview": compact_console_text(text),
            "threadId": result.thread_id,
            "durationMs": result.duration_ms,
            "outputLength": len(result.text),
        },
    )
    return {
        "conversationId": conversation["id"],
        "codexThreadId": result.thread_id,
        "userMessage": user_message,
        "assistantMessage": assistant_message,
        "agentRun": agent_run,
    }


def powan_label(node: dict[str, Any] | None) -> str:
    if not node:
        return "名前のないポワン"
    return str(node.get("title") or node.get("body") or "名前のないポワン").strip() or "名前のないポワン"


def document_nodes(document: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = document.get("nodes") or []
    return [node for node in nodes if isinstance(node, dict) and not node.get("archived")]


def document_node(document: dict[str, Any], node_id: str) -> dict[str, Any]:
    for node in document_nodes(document):
        if str(node.get("id") or "") == str(node_id):
            return node
    raise HTTPException(status_code=404, detail="Powan not found")


def document_direct_children(document: dict[str, Any], parent_id: str) -> list[dict[str, Any]]:
    return [node for node in document_nodes(document) if str(node.get("parent") or "") == str(parent_id)]


def resolve_discord_project(project: str) -> str:
    clean = str(project or "").strip()
    if clean:
        return STORE.safe_project_name(clean)
    raise RuntimeError("Discord project is required")


def resolve_discord_target_powan(payload: dict[str, Any]) -> tuple[str, str, str, str]:
    project = resolve_discord_project(str(payload.get("project") or ""))
    file = STORE.safe_powan_name(str(payload.get("file") or DEFAULT_FILE))
    document = STORE.load_document(project, file)
    target_node_id = str(payload.get("targetNodeId") or "").strip()
    if target_node_id:
        target_node = document_node(document, target_node_id)
    else:
        roots = [node for node in document_nodes(document) if not node.get("parent")]
        if not roots:
            raise RuntimeError("Discord target powan is missing")
        target_node = roots[0]
        target_node_id = str(target_node.get("id") or "")
    if not target_node_id:
        raise RuntimeError("Discord target powan id is missing")
    return project, file, target_node_id, powan_label(target_node)


def handle_discord_powan_message(payload: dict[str, Any]) -> dict[str, Any]:
    project, file, target_node_id, target_label = resolve_discord_target_powan(payload)
    content = str(payload.get("content") or "").strip()
    if not content:
        return {"ok": True, "reply": "", "displayName": target_label}
    author_name = str(payload.get("authorName") or "Discord user")
    author_id = str(payload.get("authorId") or "")
    channel_id = str(payload.get("channelId") or "")
    message_id = str(payload.get("messageId") or "")
    incoming_message = {
        "kind": "operator_message",
        "source": "discord",
        "from": {
            "kind": "discord_user",
            "id": author_id,
            "name": author_name,
        },
        "to": {
            "kind": "powan",
            "id": target_node_id,
            "name": target_label,
        },
        "operatorMessage": content,
        "parentCommand": "",
        "childReplies": [],
        "body": content,
        "allowedAction": "may_command_children",
        "systemInstruction": "これはDiscordからこのポワンへの入力です。from.kind と本文を見て返答してください。",
        "discord": {
            "channelId": channel_id,
            "messageId": message_id,
        },
    }
    result = run_powan_codex_message(
        target_node_id,
        project=project,
        file=file,
        text=content,
        include_meaning_tree=False,
        include_direct_child_code=False,
        attachments=[],
        source="discord",
        sender_node_id=None,
        sender_label_override=author_name,
        incoming_message=incoming_message,
    )
    assistant_message = result.get("assistantMessage") if isinstance(result.get("assistantMessage"), dict) else None
    return {
        "ok": True,
        "reply": str((assistant_message or {}).get("text") or ""),
        "displayName": target_label,
        "conversationId": result.get("conversationId"),
        "agentRunId": (result.get("agentRun") or {}).get("id") if isinstance(result.get("agentRun"), dict) else None,
    }


ABC_DISCORD_BRIDGE = AbcDiscordBridge(
    root_dir=APP_ROOT,
    log_event=log_server_event,
    message_handler=handle_discord_powan_message,
)


@app.on_event("startup")
def start_discord_bridge() -> None:
    if ABC_DISCORD_BRIDGE is None:
        return
    ABC_DISCORD_BRIDGE.apply_settings(load_app_settings())


@app.on_event("shutdown")
def stop_discord_bridge() -> None:
    if ABC_DISCORD_BRIDGE is not None:
        ABC_DISCORD_BRIDGE.stop("server-shutdown")


def match_child_command_target(children: list[dict[str, Any]], item: ChildCommandRequest) -> dict[str, Any]:
    child_id = str(item.childId or "").strip()
    title = item.title.strip()
    body = item.body.strip()
    if child_id:
        matches = [child for child in children if str(child.get("id") or "") == child_id]
    else:
        if not title and not body:
            raise HTTPException(status_code=400, detail="child title or body is required")
        matches = children
        if title:
            matches = [child for child in matches if str(child.get("title") or "").strip() == title]
        if body:
            matches = [child for child in matches if str(child.get("body") or "").strip() == body]
    if not matches:
        raise HTTPException(status_code=404, detail="Child powan not found")
    if len(matches) > 1:
        raise HTTPException(status_code=409, detail="Multiple child powans matched")
    return matches[0]


def render_child_command(parent: dict[str, Any], child: dict[str, Any], instruction: str) -> str:
    return f"""親ポワン「{powan_label(parent)}」から、あなたへの命令です。
あなたは親ポワンの直接の子ポワン「{powan_label(child)}」として、この命令を実行してください。
必要な状態変更は `.agents/skills/abc-powan/TOOL.md` の操作を使ってください。

{instruction.strip()}
"""


def render_child_return_message(parent_label: str, result: dict[str, Any]) -> str:
    child_label = str(result.get("meaning") or "名前のないポワン").strip() or "名前のないポワン"
    status = str(result.get("status") or "").strip() or "unknown"
    dispatch_session_id = str(result.get("dispatchSessionId") or "").strip()
    dispatch_id = result.get("dispatchId")
    conversation_id = result.get("conversationId")
    assistant_message = result.get("assistantMessage") if isinstance(result.get("assistantMessage"), dict) else None
    reply_text = str((assistant_message or {}).get("text") or "").strip()
    error_text = str(result.get("error") or "").strip()
    lines = [
        f"子ポワン「{child_label}」から、親ポワン「{parent_label}」へ返事が戻りました。",
        "",
        f"状態: {status}",
    ]
    if conversation_id is not None:
        lines.append(f"子会話ID: {conversation_id}")
    if dispatch_session_id:
        lines.append(f"一括指示ID: {dispatch_session_id}")
    if dispatch_id is not None:
        lines.append(f"送信ID: {dispatch_id}")
    if reply_text:
        lines.extend(["", "--- 子ポワンの返事 ---", reply_text])
    elif error_text:
        lines.extend(["", "--- エラー ---", error_text])
    else:
        lines.extend(["", "子ポワンの返事本文はありません。"])
    return "\n".join(lines).strip()


def render_child_return_bundle_message(parent_label: str, results: list[dict[str, Any]], dispatch_session_id: str) -> str:
    lines: list[str] = []
    for index, result in enumerate(results, start=1):
        child_label = str(result.get("meaning") or "名前のないポワン").strip() or "名前のないポワン"
        status = str(result.get("status") or "").strip() or "unknown"
        conversation_id = result.get("conversationId")
        dispatch_id = result.get("dispatchId")
        assistant_message = result.get("assistantMessage") if isinstance(result.get("assistantMessage"), dict) else None
        reply_text = str((assistant_message or {}).get("text") or "").strip()
        error_text = str(result.get("error") or "").strip()
        lines.extend(["", f"## {index}. {child_label}", f"状態: {status}"])
        if conversation_id is not None:
            lines.append(f"子会話ID: {conversation_id}")
        if dispatch_id is not None:
            lines.append(f"送信ID: {dispatch_id}")
        if reply_text:
            lines.extend(["", reply_text])
        elif error_text:
            lines.extend(["", f"エラー: {error_text}"])
        else:
            lines.extend(["", "返事本文なし。"])
    return "\n".join(lines).strip()


def child_command_skip_reason(item: ChildCommandRequest) -> str:
    if item.skip:
        return item.skipReason.strip() or "skip=true"
    status = str(getattr(item, "status", "") or "").strip().lower()
    if status in {"skip", "skipped", "noop", "no-op", "none"}:
        return item.skipReason.strip() or f"status={status}"
    instruction = item.instruction.strip()
    if "今回の修正対象ではありません" in instruction:
        return "not target"
    if "作業不要" in instruction and "現状維持" in instruction:
        return "no work requested"
    return ""


def child_command_jobs(document: dict[str, Any], parent_id: str, request: CommandChildrenRequest) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    parent = document_node(document, parent_id)
    children = document_direct_children(document, parent_id)
    if not children:
        raise HTTPException(status_code=400, detail="Child powans are required")
    common_instruction = request.instruction.strip()
    jobs_by_id: dict[str, dict[str, str]] = {}
    skipped_by_id: dict[str, dict[str, str]] = {}
    if common_instruction:
        for child in children:
            child_id = str(child.get("id") or "")
            if child_id:
                jobs_by_id[child_id] = {
                    "nodeId": child_id,
                    "meaning": powan_label(child),
                    "instruction": common_instruction,
                }
    for item in request.instructions:
        child = match_child_command_target(children, item)
        child_id = str(child.get("id") or "")
        if not child_id:
            continue
        skip_reason = child_command_skip_reason(item)
        if skip_reason:
            jobs_by_id.pop(child_id, None)
            skipped_by_id[child_id] = {
                "nodeId": child_id,
                "meaning": powan_label(child),
                "instruction": item.instruction.strip(),
                "skipReason": skip_reason,
            }
            continue
        individual_instruction = item.instruction.strip()
        if not individual_instruction and not common_instruction:
            raise HTTPException(status_code=400, detail="instruction is required")
        if child_id in jobs_by_id and not common_instruction:
            raise HTTPException(status_code=409, detail="Duplicate child command target")
        instruction = common_instruction
        if individual_instruction:
            instruction = f"{common_instruction}\n\n個別命令:\n{individual_instruction}".strip()
        jobs_by_id[child_id] = {
            "nodeId": child_id,
            "meaning": powan_label(child),
            "instruction": instruction,
        }
    if not jobs_by_id:
        if skipped_by_id:
            return [], list(skipped_by_id.values())
        raise HTTPException(status_code=400, detail="instruction or instructions is required")
    jobs: list[dict[str, str]] = []
    for child in children:
        child_id = str(child.get("id") or "")
        job = jobs_by_id.get(child_id)
        if job:
            jobs.append(
                {
                    **job,
                    "text": render_child_command(parent, child, job["instruction"]),
                }
            )
    return jobs, list(skipped_by_id.values())


@app.get("/api/conversation-history")
def list_conversation_history(project: str, file: str = DEFAULT_FILE) -> dict[str, Any]:
    STORE.load_document(project, file)
    return STORE.list_document_conversation_sessions(project, file)


@app.get("/api/bulk-conversation-history")
def list_bulk_conversation_history(project: str, file: str = DEFAULT_FILE) -> dict[str, Any]:
    STORE.load_document(project, file)
    return STORE.list_bulk_command_sessions(project, file)


@app.post("/api/bulk-conversation-history")
def upsert_bulk_conversation_history(request: BulkCommandHistoryRequest) -> dict[str, Any]:
    STORE.load_document(request.project, request.file)
    return STORE.upsert_bulk_command_session(
        request.project,
        request.file,
        request.id,
        request.targetIds,
        request.targetNames,
        [base_model_payload(message) for message in request.messages],
        created_at=request.createdAt,
        updated_at=request.updatedAt,
    )


@app.get("/api/conversations/{node_id}")
def list_conversation_messages(node_id: str, project: str, file: str = DEFAULT_FILE) -> dict[str, Any]:
    ensure_powan_exists(project, file, node_id)
    return live_conversation_payload(project, file, node_id)


@app.get("/api/conversations/{node_id}/sessions")
def list_conversation_sessions(node_id: str, project: str, file: str = DEFAULT_FILE) -> dict[str, Any]:
    ensure_powan_exists(project, file, node_id)
    return STORE.list_conversation_sessions(project, file, node_id)


@app.get("/api/conversations/{node_id}/sessions/{conversation_id}")
def get_conversation_session(
    node_id: str,
    conversation_id: int,
    project: str,
    file: str = DEFAULT_FILE,
) -> dict[str, Any]:
    ensure_powan_exists(project, file, node_id)
    return live_conversation_payload(project, file, node_id, conversation_id)


@app.get("/api/agent-runs/running")
def list_running_agent_runs(project: str, file: str = DEFAULT_FILE) -> dict[str, Any]:
    STORE.load_document(project, file)
    runs = reconcile_running_agent_runs(project, file)
    return {"runs": runs, "count": len(runs)}


@app.post("/api/conversations/{node_id}/messages")
def append_conversation_message(
    node_id: str,
    request: ConversationMessageRequest,
    project: str,
    file: str = DEFAULT_FILE,
) -> dict[str, Any]:
    ensure_powan_exists(project, file, node_id)
    return STORE.append_conversation_message(project, file, node_id, request.role, request.text)


@app.post("/api/conversations/{node_id}/sessions")
def start_new_conversation_session(node_id: str, project: str, file: str = DEFAULT_FILE) -> dict[str, Any]:
    ensure_powan_exists(project, file, node_id)
    conversation = STORE.start_new_conversation(project, file, node_id)
    payload = STORE.list_conversation_messages(project, file, node_id)
    log_server_event(
        "info",
        "conversation-session-started",
        {
            "project": STORE.safe_project_name(project),
            "file": STORE.safe_powan_name(file),
            "nodeId": node_id,
            "conversationId": conversation["id"],
        },
    )
    return {
        "conversationId": conversation["id"],
        "conversation": conversation,
        "messages": payload["messages"],
    }


@app.post("/api/conversations/{node_id}/summarize")
def summarize_conversation(node_id: str, project: str, file: str = DEFAULT_FILE) -> dict[str, Any]:
    ensure_powan_exists(project, file, node_id)
    messages = STORE.list_conversation_messages(project, file, node_id)["messages"]
    if not messages:
        conversation = STORE.start_new_conversation(project, file, node_id)
        return {
            "conversationId": conversation["id"],
            "conversation": conversation,
            "summary": "",
            "messages": [],
        }
    old_conversation = STORE.active_conversation(project, file, node_id)
    project_root_path = STORE.project_root(project)
    settings = load_app_settings()
    codex_model = normalize_codex_model(settings.get("codexModel"))
    codex_reasoning_effort = normalize_codex_reasoning_effort(settings.get("codexReasoningEffort"))
    log_server_event(
        "info",
        "conversation-summary-start",
        {
            "project": STORE.safe_project_name(project),
            "file": STORE.safe_powan_name(file),
            "nodeId": node_id,
            "conversationId": old_conversation["id"],
            "messageCount": len(messages),
            "codexModel": codex_model,
            "codexReasoningEffort": codex_reasoning_effort,
        },
    )
    try:
        result = CODEX_BRIDGE.summarize_conversation(
            project_root=project_root_path,
            project=STORE.safe_project_name(project),
            document_name=STORE.safe_powan_name(file),
            node_id=node_id,
            messages=messages,
            codex_model=codex_model,
            codex_reasoning_effort=codex_reasoning_effort,
        )
    except Exception as exc:
        detail = f"Codex exec crashed before summarizing: {exc}"
        log_server_event(
            "error",
            "conversation-summary-crashed",
            {
                "project": STORE.safe_project_name(project),
                "file": STORE.safe_powan_name(file),
                "nodeId": node_id,
                "conversationId": old_conversation["id"],
                "error": repr(exc),
            },
        )
        raise HTTPException(status_code=502, detail=detail) from exc
    if result.returncode != 0 or not result.text:
        STORE.record_agent_run(
            project,
            old_conversation["id"],
            node_id,
            "failed",
            {
                "type": "conversation-summary",
                "project": STORE.safe_project_name(project),
                "file": STORE.safe_powan_name(file),
                "nodeId": node_id,
                "conversationId": old_conversation["id"],
                "durationMs": result.duration_ms,
                "inputChars": result.input_chars,
                "turnCount": result.turn_count,
                "retryCount": result.retry_count,
                "trimmedChars": result.trimmed_chars,
            },
            output_text=result.text,
            error_text=result.stderr[-4000:],
        )
        log_server_event(
            "error",
            "conversation-summary-failed",
            {
                "project": STORE.safe_project_name(project),
                "file": STORE.safe_powan_name(file),
                "nodeId": node_id,
                "conversationId": old_conversation["id"],
                "returncode": result.returncode,
                "stderr": result.stderr[-1000:],
            },
        )
        raise HTTPException(status_code=502, detail="Codex exec summary failed")
    STORE.record_agent_run(
        project,
        old_conversation["id"],
        node_id,
        "completed",
        {
            "type": "conversation-summary",
            "project": STORE.safe_project_name(project),
            "file": STORE.safe_powan_name(file),
            "nodeId": node_id,
            "conversationId": old_conversation["id"],
            "durationMs": result.duration_ms,
            "inputChars": result.input_chars,
            "turnCount": result.turn_count,
            "retryCount": result.retry_count,
            "trimmedChars": result.trimmed_chars,
        },
        output_text=result.text,
        error_text=result.stderr[-4000:],
    )
    conversation = STORE.start_new_conversation(project, file, node_id, title="要約から再開", summary_text=result.text)
    payload = STORE.list_conversation_messages(project, file, node_id)
    log_server_event(
        "info",
        "conversation-summary-complete",
        {
            "project": STORE.safe_project_name(project),
            "file": STORE.safe_powan_name(file),
            "nodeId": node_id,
            "oldConversationId": old_conversation["id"],
            "conversationId": conversation["id"],
            "summaryLength": len(result.text),
            "inputChars": result.input_chars,
            "turnCount": result.turn_count,
            "retryCount": result.retry_count,
            "trimmedChars": result.trimmed_chars,
        },
    )
    return {
        "conversationId": conversation["id"],
        "conversation": conversation,
        "summary": result.text,
        "inputChars": result.input_chars,
        "turnCount": result.turn_count,
        "retryCount": result.retry_count,
        "trimmedChars": result.trimmed_chars,
        "messages": payload["messages"],
    }


@app.post("/api/conversations/{node_id}/codex")
def talk_to_powan_with_codex(
    node_id: str,
    request: PowanCodexRequest,
    project: str,
    file: str = DEFAULT_FILE,
) -> dict[str, Any]:
    return run_powan_codex_message(
        node_id,
        project=project,
        file=file,
        text=request.text,
        include_meaning_tree=bool(request.includeMeaningTree),
        include_direct_child_code=bool(request.includeDirectChildCode),
        attachments=request.attachments,
        source="conversation",
    )


@app.get("/api/powan-work-events")
def list_powan_work_events(
    project: str,
    file: str = DEFAULT_FILE,
    after: int = 0,
    conversationId: int | None = None,
) -> dict[str, Any]:
    safe_project = STORE.safe_project_name(project)
    safe_file = STORE.safe_powan_name(file)
    with POWAN_WORK_EVENT_LOCK:
        events = [
            event
            for event in POWAN_WORK_EVENTS
            if int(event.get("sequence") or 0) > after
            and event.get("project") == safe_project
            and event.get("file") == safe_file
            and (conversationId is None or event.get("conversationId") == conversationId)
        ]
        latest_sequence = POWAN_WORK_EVENT_SEQUENCE
    return {
        "events": events,
        "latestSequence": latest_sequence,
    }


@app.post("/api/ai/powans/{node_id}/actions/command-children")
def command_child_powans(node_id: str, request: CommandChildrenRequest) -> dict[str, Any]:
    request_payload = base_model_payload(request)
    active_key = f"{STORE.safe_project_name(request.project)}\n{STORE.safe_powan_name(request.file)}\n{node_id}"
    parent_label = "名前のないポワン"
    parent_conversation_id = 0
    job_count = 0
    dispatch_session_id = ""
    release_active_key_in_finally = False
    try:
        document = STORE.load_document(request.project, request.file)
        parent = document_node(document, node_id)
        parent_label = powan_label(parent)
        parent_conversation = STORE.active_conversation(request.project, request.file, node_id)
        parent_conversation_id = int(parent_conversation["id"])
        jobs, skipped_jobs = child_command_jobs(document, node_id, request)
        job_count = len(jobs)
        skipped_results = [
            {
                "nodeId": item["nodeId"],
                "meaning": item["meaning"],
                "instruction": item.get("instruction", ""),
                "renderedText": "",
                "status": "skipped",
                "skipReason": item.get("skipReason", ""),
            }
            for item in skipped_jobs
        ]
        log_server_event(
            "info",
            "command-child-powans-jobs-prepared",
            {
                "console": True,
                "project": STORE.safe_project_name(request.project),
                "file": STORE.safe_powan_name(request.file),
                "nodeId": node_id,
                "meaning": parent_label,
                "jobCount": job_count,
                "skippedCount": len(skipped_results),
                "jobs": [
                    {
                        "index": index,
                        "nodeId": job["nodeId"],
                        "meaning": job["meaning"],
                        "instructionLength": len(job["instruction"]),
                        "renderedTextLength": len(job["text"]),
                    }
                    for index, job in enumerate(jobs)
                ],
                "skipped": skipped_results,
            },
        )
        if skipped_results and not jobs:
            response_payload = {
                "project": STORE.safe_project_name(request.project),
                "file": STORE.safe_powan_name(request.file),
                "parent": {
                    "id": node_id,
                    "meaning": parent_label,
                },
                "detached": False,
                "results": skipped_results,
            }
            log_server_event(
                "info",
                "command-child-powans-all-skipped",
                {
                    "console": True,
                    "project": STORE.safe_project_name(request.project),
                    "file": STORE.safe_powan_name(request.file),
                    "nodeId": node_id,
                    "meaning": parent_label,
                    "skippedCount": len(skipped_results),
                    "results": skipped_results,
                },
            )
            record_api_action_safely(
                project=request.project,
                file=request.file,
                node_id=node_id,
                action="command-children",
                status="completed",
                request_payload=request_payload,
                response_payload=response_payload,
            )
            return response_payload
        with COMMAND_CHILDREN_ACTIVE_LOCK:
            if active_key in COMMAND_CHILDREN_ACTIVE_KEYS:
                log_server_event(
                    "warn",
                    "command-child-powans-duplicate-rejected",
                    {
                        "console": True,
                        "project": STORE.safe_project_name(request.project),
                        "file": STORE.safe_powan_name(request.file),
                        "nodeId": node_id,
                        "message": "command-children already running for this parent",
                        "request": request_payload,
                    },
                )
                record_api_action_safely(
                    project=request.project,
                    file=request.file,
                    node_id=node_id,
                    action="command-children",
                    status="failed",
                    request_payload=request_payload,
                    response_payload={},
                    error_text="command-children already running for this parent",
                )
                raise HTTPException(status_code=409, detail="command-children already running for this parent")
            COMMAND_CHILDREN_ACTIVE_KEYS.add(active_key)
            release_active_key_in_finally = True
        dispatch_session_id = f"childcmd-{uuid4().hex}"
        dispatch_interval_ms = 100
        worker_count = max(1, len(jobs))
        STORE.create_child_command_session(
            request.project,
            request.file,
            dispatch_session_id,
            node_id,
            request.instruction,
            request_payload,
            len(jobs),
        )
        results: list[dict[str, Any]] = []
        start_message = f"{parent_label} -> 子ポワン {len(jobs)}件 / 一括命令受信"
        log_server_event(
            "info",
            "command-child-powans-start",
            {
                "console": True,
                "message": start_message,
                "project": STORE.safe_project_name(request.project),
                "file": STORE.safe_powan_name(request.file),
                "nodeId": node_id,
                "meaning": parent_label,
                "count": len(jobs),
                "instructionPreview": compact_console_text(request.instruction),
                "includeMeaningTree": bool(request.includeMeaningTree),
                "continueAfterChildReplies": bool(request.continueAfterChildReplies),
                "dispatchSessionId": dispatch_session_id,
                "dispatchIntervalMs": dispatch_interval_ms,
                "request": request_payload,
            },
        )
        remember_powan_batch_work_event(
            status="received",
            message=start_message,
            project=request.project,
            file=request.file,
            source="command-children",
            sender_id=node_id,
            sender_label=parent_label,
            receiver_label=f"子ポワン {len(jobs)}件",
            count=len(jobs),
            instruction=request.instruction,
            extra={
                "includeMeaningTree": bool(request.includeMeaningTree),
                "continueAfterChildReplies": bool(request.continueAfterChildReplies),
                "dispatchSessionId": dispatch_session_id,
                "dispatchIntervalMs": dispatch_interval_ms,
            },
        )

        for job in jobs:
            child_conversation = STORE.active_conversation(request.project, request.file, job["nodeId"])
            log_powan_work_status(
                "received",
                project=request.project,
                file=request.file,
                source="command-children",
                sender_id=node_id,
                sender_label=parent_label,
                receiver_id=job["nodeId"],
                receiver_label=job["meaning"],
                conversation_id=child_conversation["id"],
                extra={
                    "textPreview": compact_console_text(job["text"]),
                    "messageLength": len(job["text"].strip()),
                    "includeMeaningTree": bool(request.includeMeaningTree),
                    "includeDirectChildCode": False,
                    "attachmentCount": 0,
                    "preStored": True,
                },
            )
            user_message = STORE.append_conversation_message(
                request.project,
                request.file,
                job["nodeId"],
                "user",
                conversation_record_text(job["text"], []),
            )
            log_server_event(
                "info",
                "powan-user-message-appended",
                {
                    "project": STORE.safe_project_name(request.project),
                    "file": STORE.safe_powan_name(request.file),
                    "nodeId": job["nodeId"],
                    "conversationId": child_conversation["id"],
                    "messageId": user_message.get("id"),
                    "source": "command-children",
                    "senderNodeId": node_id,
                    "messageLength": len(job["text"].strip()),
                    "preStored": True,
                },
            )
            job["conversationId"] = child_conversation["id"]
            job["userMessage"] = user_message
            dispatch = STORE.record_child_command_dispatch(
                request.project,
                request.file,
                dispatch_session_id,
                node_id,
                job["nodeId"],
                job["meaning"],
                job["instruction"],
                job["text"],
                int(child_conversation["id"]),
                int(user_message["id"]),
            )
            job["dispatchId"] = dispatch["id"]
        STORE.update_child_command_session_status(request.project, request.file, dispatch_session_id, "sent")

        def run_parent_followup_from_child_returns(results: list[dict[str, Any]]) -> dict[str, Any] | None:
            if not results:
                return None
            parent_text = render_child_return_bundle_message(parent_label, results, dispatch_session_id)
            if not parent_text:
                return None
            parent_message = STORE.append_conversation_message_to_conversation(
                request.project,
                request.file,
                node_id,
                parent_conversation_id,
                "user",
                parent_text,
            )
            sender_id = str(results[0].get("nodeId") or "") if len(results) == 1 else None
            incoming_message = child_return_incoming_message(
                parent_id=node_id,
                parent_label=parent_label,
                parent_conversation_id=int(parent_conversation_id),
                parent_message_id=int(parent_message["id"]) if parent_message.get("id") is not None else None,
                parent_text=parent_text,
                results=results,
                continue_after_child_replies=bool(request.continueAfterChildReplies),
                dispatch_session_id=dispatch_session_id,
            )
            log_server_event(
                "info",
                "command-child-powans-parent-followup-start",
                {
                    "console": True,
                    "project": STORE.safe_project_name(request.project),
                    "file": STORE.safe_powan_name(request.file),
                    "parentId": node_id,
                    "parentMeaning": parent_label,
                    "parentConversationId": parent_conversation_id,
                    "parentMessageId": parent_message.get("id"),
                    "senderNodeId": sender_id,
                    "dispatchSessionId": dispatch_session_id,
                    "continueAfterChildReplies": bool(request.continueAfterChildReplies),
                    "allowedAction": incoming_message.get("allowedAction"),
                    "childResultCount": len(results),
                },
            )
            followup = run_powan_codex_message(
                node_id,
                project=request.project,
                file=request.file,
                text=parent_text,
                include_meaning_tree=bool(request.includeMeaningTree),
                include_direct_child_code=False,
                attachments=[],
                source="command-child-return",
                sender_node_id=sender_id,
                sender_label_override="子ポワン一括返答",
                pre_appended_user_message=parent_message,
                incoming_message=incoming_message,
            )
            log_server_event(
                "info",
                "command-child-powans-parent-followup-complete",
                {
                    "console": True,
                    "project": STORE.safe_project_name(request.project),
                    "file": STORE.safe_powan_name(request.file),
                    "parentId": node_id,
                    "parentMeaning": parent_label,
                    "parentConversationId": followup.get("conversationId"),
                    "assistantMessageId": (followup.get("assistantMessage") or {}).get("id") if isinstance(followup.get("assistantMessage"), dict) else None,
                    "agentRunId": (followup.get("agentRun") or {}).get("id") if isinstance(followup.get("agentRun"), dict) else None,
                    "dispatchSessionId": dispatch_session_id,
                    "childResultCount": len(results),
                },
            )
            return followup

        def run_job(index: int, job: dict[str, Any]) -> dict[str, Any]:
            delay_ms = dispatch_interval_ms * index
            if delay_ms:
                time.sleep(delay_ms / 1000)
            log_server_event(
                "trace",
                "command-child-powan-job-start",
                {
                    "project": STORE.safe_project_name(request.project),
                    "file": STORE.safe_powan_name(request.file),
                    "parentId": node_id,
                    "nodeId": job["nodeId"],
                    "index": index,
                    "delayMs": delay_ms,
                    "instruction": job["instruction"],
                },
            )
            try:
                if job.get("dispatchId") is not None:
                    STORE.mark_child_command_dispatch_started(request.project, int(job["dispatchId"]))
                log_server_event(
                    "info",
                    "command-child-powan-before-run",
                    {
                        "project": STORE.safe_project_name(request.project),
                        "file": STORE.safe_powan_name(request.file),
                        "parentId": node_id,
                        "parentMeaning": parent_label,
                        "nodeId": job["nodeId"],
                        "meaning": job["meaning"],
                        "index": index,
                        "delayMs": delay_ms,
                        "renderedTextLength": len(job["text"]),
                        "instructionLength": len(job["instruction"]),
                        "dispatchSessionId": dispatch_session_id,
                        "dispatchId": job.get("dispatchId"),
                        "dispatchIntervalMs": dispatch_interval_ms,
                    },
                )
                result = run_powan_codex_message(
                    job["nodeId"],
                    project=request.project,
                    file=request.file,
                    text=job["text"],
                    include_meaning_tree=bool(request.includeMeaningTree),
                    attachments=[],
                    source="command-children",
                    sender_node_id=node_id,
                    pre_appended_user_message=job.get("userMessage") if isinstance(job.get("userMessage"), dict) else None,
                )
                run_status = "cancelled" if result.get("cancelled") else "completed"
                item = {
                    "nodeId": job["nodeId"],
                    "meaning": job["meaning"],
                    "instruction": job["instruction"],
                    "renderedText": job["text"],
                    "status": run_status,
                    "dispatchSessionId": dispatch_session_id,
                    "dispatchId": job.get("dispatchId"),
                    "conversationId": result.get("conversationId"),
                    "userMessage": result.get("userMessage"),
                    "assistantMessage": result.get("assistantMessage"),
                    "agentRun": result.get("agentRun"),
                }
                if job.get("dispatchId") is not None:
                    assistant_message = result.get("assistantMessage") if isinstance(result.get("assistantMessage"), dict) else None
                    agent_run = result.get("agentRun") if isinstance(result.get("agentRun"), dict) else None
                    STORE.mark_child_command_dispatch_replied(
                        request.project,
                        int(job["dispatchId"]),
                        run_status,
                        int(assistant_message["id"]) if assistant_message and assistant_message.get("id") is not None else None,
                        int(agent_run["id"]) if agent_run and agent_run.get("id") is not None else None,
                    )
                item["parentReturnText"] = render_child_return_message(parent_label, item)
                log_server_event(
                    "trace",
                    "command-child-powan-job-complete",
                    {
                        "project": STORE.safe_project_name(request.project),
                        "file": STORE.safe_powan_name(request.file),
                        "parentId": node_id,
                        "nodeId": job["nodeId"],
                        "index": index,
                        "status": run_status,
                        "dispatchSessionId": dispatch_session_id,
                        "dispatchId": job.get("dispatchId"),
                    },
                )
                return item
            except HTTPException as exc:
                if job.get("dispatchId") is not None:
                    STORE.mark_child_command_dispatch_replied(request.project, int(job["dispatchId"]), "failed", error_text=str(exc.detail))
                failure = {
                    "nodeId": job["nodeId"],
                    "meaning": job["meaning"],
                    "instruction": job["instruction"],
                    "renderedText": job["text"],
                    "status": "failed",
                    "dispatchSessionId": dispatch_session_id,
                    "dispatchId": job.get("dispatchId"),
                    "conversationId": job.get("conversationId"),
                    "userMessage": job.get("userMessage"),
                    "error": exc.detail,
                    "httpStatus": exc.status_code,
                }
                failure["parentReturnText"] = render_child_return_message(parent_label, failure)
                log_server_event(
                    "error",
                    "command-child-powan-failed",
                    {
                        "project": STORE.safe_project_name(request.project),
                        "file": STORE.safe_powan_name(request.file),
                        "parentId": node_id,
                        "nodeId": job["nodeId"],
                        "instruction": job["instruction"],
                        "renderedText": job["text"],
                        "error": exc.detail,
                    },
                )
                return failure
            except Exception as exc:
                if job.get("dispatchId") is not None:
                    STORE.mark_child_command_dispatch_replied(request.project, int(job["dispatchId"]), "failed", error_text=repr(exc))
                failure = {
                    "nodeId": job["nodeId"],
                    "meaning": job["meaning"],
                    "instruction": job["instruction"],
                    "renderedText": job["text"],
                    "status": "failed",
                    "dispatchSessionId": dispatch_session_id,
                    "dispatchId": job.get("dispatchId"),
                    "conversationId": job.get("conversationId"),
                    "userMessage": job.get("userMessage"),
                    "error": repr(exc),
                    "httpStatus": 500,
                }
                failure["parentReturnText"] = render_child_return_message(parent_label, failure)
                log_server_event(
                    "error",
                    "command-child-powan-failed",
                    {
                        "project": STORE.safe_project_name(request.project),
                        "file": STORE.safe_powan_name(request.file),
                        "parentId": node_id,
                        "nodeId": job["nodeId"],
                        "instruction": job["instruction"],
                        "renderedText": job["text"],
                        "error": repr(exc),
                    },
                )
                return failure

        def run_batch_detached() -> None:
            results: list[dict[str, Any]] = []
            try:
                ordered_results: list[dict[str, Any] | None] = [None] * len(jobs)
                with ThreadPoolExecutor(max_workers=worker_count) as executor:
                    futures = {
                        executor.submit(run_job, index, job): index
                        for index, job in enumerate(jobs)
                    }
                    for future in as_completed(futures):
                        index = futures[future]
                        ordered_results[index] = future.result()
                results = [result for result in ordered_results if result is not None]

                for result in results:
                    result.pop("httpStatus", None)

                response = {
                    "project": STORE.safe_project_name(request.project),
                    "file": STORE.safe_powan_name(request.file),
                    "parent": {"id": node_id, "meaning": powan_label(parent)},
                    "detached": True,
                    "dispatchSessionId": dispatch_session_id,
                    "dispatchIntervalMs": dispatch_interval_ms,
                    "continueAfterChildReplies": bool(request.continueAfterChildReplies),
                    "results": results,
                }
                complete_message = f"{parent_label} -> 子ポワン {len(results)}件 / 一括命令完了"
                log_server_event(
                    "info",
                    "command-child-powans-complete",
                    {
                        "console": True,
                        "message": complete_message,
                        "project": STORE.safe_project_name(request.project),
                        "file": STORE.safe_powan_name(request.file),
                        "nodeId": node_id,
                        "meaning": parent_label,
                        "count": len(results),
                        "failed": sum(1 for result in results if result.get("status") != "completed"),
                        "instructionPreview": compact_console_text(request.instruction),
                        "request": request_payload,
                        "response": response,
                    },
                )
                session_status = "completed" if all(result.get("status") == "completed" for result in results) else "failed"
                STORE.update_child_command_session_status(request.project, request.file, dispatch_session_id, session_status)
                remember_powan_batch_work_event(
                    status="completed",
                    message=complete_message,
                    project=request.project,
                    file=request.file,
                    source="command-children",
                    sender_id=node_id,
                    sender_label=parent_label,
                    receiver_label=f"子ポワン {len(results)}件",
                    count=len(results),
                    instruction=request.instruction,
                    extra={
                        "detached": True,
                        "failed": sum(1 for result in results if result.get("status") != "completed"),
                        "dispatchSessionId": dispatch_session_id,
                        "dispatchIntervalMs": dispatch_interval_ms,
                        "continueAfterChildReplies": bool(request.continueAfterChildReplies),
                    },
                )
                with COMMAND_CHILDREN_ACTIVE_LOCK:
                    COMMAND_CHILDREN_ACTIVE_KEYS.discard(active_key)
                parent_followup = None
                try:
                    parent_followup = run_parent_followup_from_child_returns(results)
                except Exception as exc:
                    log_server_event(
                        "error",
                        "command-child-powans-parent-followup-failed",
                        {
                            "console": True,
                            "project": STORE.safe_project_name(request.project),
                            "file": STORE.safe_powan_name(request.file),
                            "parentId": node_id,
                            "parentMeaning": parent_label,
                            "parentConversationId": parent_conversation_id,
                            "dispatchSessionId": dispatch_session_id,
                            "error": repr(exc),
                        },
                    )
                if parent_followup:
                    response["parentFollowup"] = parent_followup
            except Exception as exc:
                STORE.update_child_command_session_status(request.project, request.file, dispatch_session_id, "failed")
                failed_message = f"{parent_label} -> 子ポワン {job_count or ''}件 / 一括命令失敗" if job_count else f"{parent_label} -> 子ポワン / 一括命令失敗"
                log_server_event(
                    "error",
                    "command-child-powans-failed",
                    {
                        "console": True,
                        "message": failed_message,
                        "project": STORE.safe_project_name(request.project),
                        "file": STORE.safe_powan_name(request.file),
                        "nodeId": node_id,
                        "meaning": parent_label,
                        "error": repr(exc),
                    },
                )
                remember_powan_batch_work_event(
                    status="failed",
                    message=failed_message,
                    project=request.project,
                    file=request.file,
                    source="command-children",
                    sender_id=node_id,
                    sender_label=parent_label,
                    receiver_label=f"子ポワン {job_count}件" if job_count else "子ポワン",
                    count=job_count,
                    instruction=request.instruction,
                    extra={"detached": True, "error": repr(exc)},
                )
            finally:
                with COMMAND_CHILDREN_ACTIVE_LOCK:
                    COMMAND_CHILDREN_ACTIVE_KEYS.discard(active_key)

        accepted_results = [
            {
                "nodeId": job["nodeId"],
                "meaning": job["meaning"],
                "instruction": job["instruction"],
                "renderedText": job["text"],
                "dispatchSessionId": dispatch_session_id,
                "dispatchId": job.get("dispatchId"),
                "conversationId": job.get("conversationId"),
                "userMessage": job.get("userMessage"),
                "status": "accepted",
            }
            for job in jobs
        ] + skipped_results
        accepted_response = {
            "project": STORE.safe_project_name(request.project),
            "file": STORE.safe_powan_name(request.file),
            "parent": {"id": node_id, "meaning": powan_label(parent)},
            "detached": True,
            "dispatchSessionId": dispatch_session_id,
            "dispatchIntervalMs": dispatch_interval_ms,
            "continueAfterChildReplies": bool(request.continueAfterChildReplies),
            "results": accepted_results,
            "skippedCount": len(skipped_results),
        }
        log_server_event(
            "info",
            "command-child-powans-accepted",
            {
                "console": True,
                "message": f"{parent_label} -> 子ポワン {len(jobs)}件 / 一括命令受付完了",
                "project": STORE.safe_project_name(request.project),
                "file": STORE.safe_powan_name(request.file),
                "nodeId": node_id,
                "meaning": parent_label,
                "count": len(jobs),
                "skippedCount": len(skipped_results),
                "detached": True,
                "dispatchSessionId": dispatch_session_id,
                "dispatchIntervalMs": dispatch_interval_ms,
                "continueAfterChildReplies": bool(request.continueAfterChildReplies),
                "request": request_payload,
                "response": accepted_response,
            },
        )
        record_api_action_safely(
            project=request.project,
            file=request.file,
            node_id=node_id,
            action="command-children",
            status="accepted",
            request_payload=request_payload,
            response_payload=accepted_response,
        )
        release_active_key_in_finally = False
        threading.Thread(
            target=run_batch_detached,
            name=f"abc-command-children-{node_id}",
            daemon=True,
        ).start()
        return accepted_response
    except HTTPException as exc:
        if dispatch_session_id:
            STORE.update_child_command_session_status(request.project, request.file, dispatch_session_id, "failed")
        failed_message = f"{parent_label} -> 子ポワン {job_count or ''}件 / 一括命令失敗" if job_count else f"{parent_label} -> 子ポワン / 一括命令失敗"
        log_server_event(
            "error",
            "command-child-powans-failed",
            {
                "console": True,
                "message": failed_message,
                "project": STORE.safe_project_name(request.project),
                "file": STORE.safe_powan_name(request.file),
                "nodeId": node_id,
                "meaning": parent_label,
                "error": str(exc.detail),
            },
        )
        remember_powan_batch_work_event(
            status="failed",
            message=failed_message,
            project=request.project,
            file=request.file,
            source="command-children",
            sender_id=node_id,
            sender_label=parent_label,
            receiver_label=f"子ポワン {job_count}件" if job_count else "子ポワン",
            count=job_count,
            instruction=request.instruction,
            extra={"error": str(exc.detail)},
        )
        record_api_action_safely(
            project=request.project,
            file=request.file,
            node_id=node_id,
            action="command-children",
            status="failed",
            request_payload=request_payload,
            response_payload={},
            error_text=str(exc.detail),
        )
        raise
    except Exception as exc:
        if dispatch_session_id:
            STORE.update_child_command_session_status(request.project, request.file, dispatch_session_id, "failed")
        failed_message = f"{parent_label} -> 子ポワン {job_count or ''}件 / 一括命令失敗" if job_count else f"{parent_label} -> 子ポワン / 一括命令失敗"
        log_server_event(
            "error",
            "command-child-powans-failed",
            {
                "console": True,
                "message": failed_message,
                "project": STORE.safe_project_name(request.project),
                "file": STORE.safe_powan_name(request.file),
                "nodeId": node_id,
                "meaning": parent_label,
                "error": repr(exc),
            },
        )
        remember_powan_batch_work_event(
            status="failed",
            message=failed_message,
            project=request.project,
            file=request.file,
            source="command-children",
            sender_id=node_id,
            sender_label=parent_label,
            receiver_label=f"子ポワン {job_count}件" if job_count else "子ポワン",
            count=job_count,
            instruction=request.instruction,
            extra={"error": repr(exc)},
        )
        record_api_action_safely(
            project=request.project,
            file=request.file,
            node_id=node_id,
            action="command-children",
            status="failed",
            request_payload=request_payload,
            response_payload={},
            error_text=repr(exc),
        )
        raise
    finally:
        if release_active_key_in_finally:
            with COMMAND_CHILDREN_ACTIVE_LOCK:
                COMMAND_CHILDREN_ACTIVE_KEYS.discard(active_key)


@app.post("/api/conversations/{node_id}/codex/cancel")
def cancel_powan_codex(
    node_id: str,
    project: str,
    file: str = DEFAULT_FILE,
) -> dict[str, Any]:
    ensure_powan_exists(project, file, node_id)
    result = CODEX_BRIDGE.cancel(
        project=STORE.safe_project_name(project),
        document_name=STORE.safe_powan_name(file),
        node_id=node_id,
    )
    log_server_event(
        "info",
        "codex-exec-cancel-api",
        {
            "project": STORE.safe_project_name(project),
            "file": STORE.safe_powan_name(file),
            "nodeId": node_id,
            **result,
        },
    )
    return result


@app.post("/api/logs/client")
def write_client_logs(batch: ClientLogBatch) -> dict[str, int]:
    if not batch.entries:
        return {"written": 0}
    written = write_log_entries(batch.entries[:500])
    return {"written": written}


@app.post("/api/shutdown")
def shutdown_app(request: ShutdownRequest) -> dict[str, Any]:
    pids = shutdown_target_pids()
    log_server_event("info", "shutdown-requested", {"reason": request.reason, "targetPids": pids})
    threading.Thread(target=shutdown_later, args=(pids,), daemon=True).start()
    return {"status": "shutting down", "targetPids": pids}


@app.post("/api/restart")
def restart_app(request: RestartRequest) -> dict[str, Any]:
    pids = shutdown_target_pids()
    settings = load_app_settings()
    visible_console = bool(settings["restartVisibleConsole"] if request.visibleConsole is None else request.visibleConsole)
    log_server_event(
        "info",
        "restart-requested",
        {
            "reason": request.reason,
            "targetPids": pids,
            "visibleConsole": visible_console,
            "visibleConsoleSource": "settings" if request.visibleConsole is None else "request",
        },
    )
    threading.Thread(target=restart_later, args=(pids, visible_console), daemon=True).start()
    return {"status": "restarting", "targetPids": pids, "visibleConsole": visible_console}
