from __future__ import annotations

import asyncio
import os
import threading
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse


DiscordMessageHandler = Callable[[dict[str, Any]], dict[str, Any]]
LogFn = Callable[[str, str, dict[str, Any] | None], None]


def normalize_discord_channel_id(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.isdecimal():
        return text
    parsed = urlparse(text)
    if parsed.netloc.lower() not in {"discord.com", "www.discord.com", "canary.discord.com", "ptb.discord.com"}:
        return text
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 3 and parts[0] == "channels" and parts[2].isdecimal():
        return parts[2]
    return text


def split_discord_message(text: str, limit: int = 1900) -> list[str]:
    normalized = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    if not normalized:
        return []
    if len(normalized) <= limit:
        return [normalized]
    chunks: list[str] = []
    rest = normalized
    while rest:
        if len(rest) <= limit:
            chunks.append(rest)
            break
        split_at = _split_index(rest, limit)
        chunks.append(rest[:split_at].rstrip())
        rest = rest[split_at:].lstrip()
    return [chunk for chunk in chunks if chunk]


def _split_index(text: str, limit: int) -> int:
    code_fence = text.rfind("```", 0, limit)
    if code_fence > 0 and text.count("```", 0, code_fence + 3) % 2 == 1:
        split_at = text.rfind("\n", 0, max(1, code_fence - 1))
        if split_at >= 300:
            return split_at
    for marker in ("\n\n", "\n"):
        split_at = text.rfind(marker, 0, limit)
        if split_at >= 300:
            return split_at
    split_at = text.rfind(" ", 0, limit)
    if split_at >= 300:
        return split_at
    return limit


def load_env_files(root_dir: Path, *, override: bool = False) -> list[str]:
    base_dir = root_dir.resolve()
    candidates = [base_dir / ".env"]
    for parent in base_dir.parents:
        candidates.append(parent / ".env")
        candidates.append(parent / "codex_agents" / "bridge" / ".env")
    loaded_paths: list[str] = []
    seen: set[Path] = set()
    loaded_keys: set[str] = set()
    for path in candidates:
        path = path.resolve()
        if path in seen:
            continue
        seen.add(path)
        if not path.is_file():
            continue
        loaded_any = False
        for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip().lstrip("\ufeff")
            if not key:
                continue
            value = value.strip().strip("\"'")
            if key in loaded_keys:
                continue
            loaded_keys.add(key)
            loaded_any = True
            current_value = os.environ.get(key)
            if override or current_value is None or not current_value.strip():
                os.environ[key] = value
            else:
                os.environ.setdefault(key, value)
        if loaded_any:
            loaded_paths.append(str(path))
    return loaded_paths


class _NullTyping:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


def _typing(channel: Any) -> Any:
    typing = getattr(channel, "typing", None)
    if callable(typing):
        return typing()
    return _NullTyping()


class AbcDiscordBridge:
    def __init__(self, *, root_dir: Path, log_event: LogFn, message_handler: DiscordMessageHandler) -> None:
        self.root_dir = root_dir
        self.log_event = log_event
        self.message_handler = message_handler
        self.lock = threading.RLock()
        self.thread: threading.Thread | None = None
        self.client: Any | None = None
        self.running_key = ""
        self.status_payload: dict[str, Any] = {
            "enabled": False,
            "running": False,
            "status": "disabled",
            "channelId": "",
            "project": "",
            "file": "",
            "targetNodeId": "",
            "error": "",
        }

    def status(self) -> dict[str, Any]:
        with self.lock:
            running = bool(self.thread and self.thread.is_alive())
            return {**self.status_payload, "running": running}

    def apply_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        config = dict(settings.get("discord") or {})
        config["channelId"] = normalize_discord_channel_id(config.get("channelId"))
        config["messageLimit"] = int(config.get("messageLimit") or 1900)
        config["messageLimit"] = max(300, min(2000, config["messageLimit"]))
        enabled = bool(config.get("enabled"))
        key = self._settings_key(config)
        with self.lock:
            if not enabled:
                self.stop("discord-settings-disabled")
                self.status_payload = self._base_status(config, status="disabled", running=False)
                return self.status()
            if self.running_key == key and self.thread and self.thread.is_alive():
                return self.status()
            self.stop("discord-settings-reload")
            loaded_env = load_env_files(self.root_dir)
            token_env = str(config.get("tokenEnv") or "DISCORD_BOT_TOKEN")
            token = os.environ.get(token_env, "").strip()
            channel_id = str(config.get("channelId") or "").strip()
            if not token:
                self.status_payload = self._base_status(
                    config,
                    status="error",
                    running=False,
                    error=f"Discord token is missing: {token_env}",
                )
                self.log_event(
                    "warn",
                    "discord-bridge-token-missing",
                    {"tokenEnv": token_env, "loadedEnv": loaded_env},
                )
                return self.status()
            if not channel_id:
                self.status_payload = self._base_status(
                    config,
                    status="error",
                    running=False,
                    error="Discord channelId is missing",
                )
                self.log_event("warn", "discord-bridge-channel-missing", {"loadedEnv": loaded_env})
                return self.status()
            self.running_key = key
            self.status_payload = self._base_status(config, status="starting", running=False)
            self.thread = threading.Thread(
                target=self._thread_main,
                args=(dict(config), token),
                name="abc-discord-bridge",
                daemon=True,
            )
            self.thread.start()
            self.log_event(
                "info",
                "discord-bridge-starting",
                {
                    "channelId": channel_id,
                    "project": str(config.get("project") or ""),
                    "file": str(config.get("file") or ""),
                    "targetNodeId": str(config.get("targetNodeId") or ""),
                    "tokenEnv": token_env,
                    "loadedEnv": loaded_env,
                },
            )
            return self.status()

    def stop(self, reason: str = "discord-bridge-stop") -> None:
        client = self.client
        if client is not None:
            try:
                loop = getattr(client, "loop", None)
                if loop and loop.is_running():
                    future = asyncio.run_coroutine_threadsafe(client.close(), loop)
                    future.result(timeout=5)
            except Exception as exc:
                self.log_event("warn", "discord-bridge-stop-error", {"reason": reason, "error": repr(exc)})
        thread = self.thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=5)
        self.client = None
        self.thread = None
        self.running_key = ""

    def _thread_main(self, config: dict[str, Any], token: str) -> None:
        try:
            import discord
        except ImportError as exc:
            with self.lock:
                self.status_payload = self._base_status(
                    config,
                    status="error",
                    running=False,
                    error="discord.py is not installed",
                )
            self.log_event("error", "discord-bridge-import-failed", {"error": repr(exc)})
            return

        channel_id = str(config.get("channelId") or "").strip()
        intents = discord.Intents.default()
        intents.message_content = True
        client = discord.Client(intents=intents)
        self.client = client

        @client.event
        async def on_ready() -> None:
            try:
                channel = await client.fetch_channel(int(channel_id))
            except Exception as exc:
                error = f"Discord channel access failed: {type(exc).__name__}"
                if getattr(exc, "code", None):
                    error = f"{error} code={getattr(exc, 'code')}"
                if type(exc).__name__ == "Forbidden":
                    error = "Discord channel access missing: Botに対象チャンネルの閲覧権限がありません"
                with self.lock:
                    self.status_payload = self._base_status(config, status="error", running=True, error=error)
                self.log_event(
                    "error",
                    "discord-bridge-channel-access-failed",
                    {"channelId": channel_id, "user": str(client.user), "error": error},
                )
                return
            with self.lock:
                self.status_payload = self._base_status(config, status="running", running=True)
            self.log_event(
                "info",
                "discord-bridge-ready",
                {
                    "channelId": channel_id,
                    "channelName": str(getattr(channel, "name", "") or ""),
                    "user": str(client.user),
                },
            )

        @client.event
        async def on_message(message: Any) -> None:
            if bool(getattr(getattr(message, "author", None), "bot", False)):
                return
            message_channel = getattr(message, "channel", None)
            message_channel_id = normalize_discord_channel_id(getattr(message_channel, "id", ""))
            if message_channel_id != channel_id:
                return
            content = str(getattr(message, "content", "") or "").strip()
            if not content:
                self.log_event(
                    "warn",
                    "discord-bridge-message-empty-content",
                    {
                        "channelId": message_channel_id,
                        "messageId": str(getattr(message, "id", "") or ""),
                        "hint": "Discord Developer PortalのMessage Content Intentが無効か、本文が空です",
                    },
                )
                return
            with self.lock:
                self.status_payload = self._base_status(config, status="running", running=True)
            await self._handle_message(config, message, content)

        try:
            client.run(token)
        except Exception as exc:
            with self.lock:
                self.status_payload = self._base_status(config, status="error", running=False, error=repr(exc))
            self.log_event("error", "discord-bridge-run-failed", {"channelId": channel_id, "error": repr(exc)})
        finally:
            with self.lock:
                if self.client is client:
                    self.client = None
                    self.thread = None
                    self.running_key = ""
                    if self.status_payload.get("status") == "running":
                        self.status_payload = self._base_status(config, status="stopped", running=False)

    async def _handle_message(self, config: dict[str, Any], message: Any, content: str) -> None:
        channel = getattr(message, "channel", None)
        author = getattr(message, "author", None)
        payload = {
            "content": content,
            "authorName": str(getattr(author, "display_name", "") or getattr(author, "name", "") or "Discord user"),
            "authorId": str(getattr(author, "id", "") or ""),
            "channelId": normalize_discord_channel_id(getattr(channel, "id", "")),
            "messageId": str(getattr(message, "id", "") or ""),
            "project": str(config.get("project") or ""),
            "file": str(config.get("file") or ""),
            "targetNodeId": str(config.get("targetNodeId") or ""),
        }
        self.log_event(
            "info",
            "discord-bridge-message-received",
            {
                "channelId": payload["channelId"],
                "messageId": payload["messageId"],
                "authorName": payload["authorName"],
                "messageLength": len(content),
            },
        )
        async with _typing(channel):
            try:
                result = await asyncio.to_thread(self.message_handler, payload)
            except Exception as exc:
                self.log_event(
                    "error",
                    "discord-bridge-message-failed",
                    {"messageId": payload["messageId"], "error": repr(exc)},
                )
                await self._send_chunks(channel, f"ABC Canvas error: {exc}", int(config.get("messageLimit") or 1900))
                return
        reply = str(result.get("reply") or "").strip()
        if not reply:
            self.log_event("warn", "discord-bridge-empty-reply", {"messageId": payload["messageId"]})
            return
        display_name = str(result.get("displayName") or "ABC Canvas").strip()
        await self._send_chunks(channel, f"**{display_name}**\n{reply}".strip(), int(config.get("messageLimit") or 1900))

    async def _send_chunks(self, channel: Any, content: str, limit: int) -> None:
        for chunk in split_discord_message(content, limit):
            await channel.send(chunk)

    def _settings_key(self, config: dict[str, Any]) -> str:
        return "\n".join(
            [
                str(config.get("enabled")),
                str(config.get("tokenEnv") or "DISCORD_BOT_TOKEN"),
                str(config.get("channelId") or ""),
                str(config.get("project") or ""),
                str(config.get("file") or ""),
                str(config.get("targetNodeId") or ""),
                str(config.get("messageLimit") or 1900),
            ]
        )

    def _base_status(
        self,
        config: dict[str, Any],
        *,
        status: str,
        running: bool,
        error: str = "",
    ) -> dict[str, Any]:
        return {
            "enabled": bool(config.get("enabled")),
            "running": running,
            "status": status,
            "channelId": str(config.get("channelId") or ""),
            "project": str(config.get("project") or ""),
            "file": str(config.get("file") or ""),
            "targetNodeId": str(config.get("targetNodeId") or ""),
            "tokenEnv": str(config.get("tokenEnv") or "DISCORD_BOT_TOKEN"),
            "messageLimit": int(config.get("messageLimit") or 1900),
            "error": error,
        }
