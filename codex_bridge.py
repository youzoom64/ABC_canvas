from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from powan_context import build_powan_context


@dataclass
class CodexRunResult:
    text: str
    thread_id: str | None
    returncode: int
    stdout: str
    stderr: str
    duration_ms: int
    resumed: bool
    command: list[str]
    input_chars: int = 0
    retry_count: int = 0
    trimmed_chars: int = 0
    turn_count: int = 0
    cancelled: bool = False


class CodexPowanBridge:
    def __init__(self, log_event, timeout_seconds: int | None = None) -> None:
        self.log_event = log_event
        self.timeout_seconds = timeout_seconds
        self.active_processes: dict[str, subprocess.Popen[str]] = {}
        self.cancelled_keys: set[str] = set()
        self.process_lock = threading.RLock()

    def cancel_key(self, project: str, document_name: str, node_id: str) -> str:
        return f"{project}\n{document_name}\n{node_id}"

    def cancel(self, *, project: str, document_name: str, node_id: str) -> dict[str, Any]:
        key = self.cancel_key(project, document_name, node_id)
        with self.process_lock:
            process = self.active_processes.get(key)
            if not process or process.poll() is not None:
                return {"cancelled": False, "running": False}
            self.cancelled_keys.add(key)
            pid = process.pid
        try:
            process.terminate()
        except OSError as exc:
            self.log_event(
                "warn",
                "codex-exec-cancel-failed",
                {"project": project, "file": document_name, "nodeId": node_id, "pid": pid, "error": str(exc)},
            )
            return {"cancelled": False, "running": True, "pid": pid, "error": str(exc)}
        self.log_event(
            "info",
            "codex-exec-cancel-requested",
            {"project": project, "file": document_name, "nodeId": node_id, "pid": pid},
        )
        return {"cancelled": True, "running": True, "pid": pid}

    def run(
        self,
        *,
        project_root: Path,
        project: str,
        document_name: str,
        document: dict[str, Any],
        node_id: str,
        user_text: str,
        conversation: dict[str, Any],
        messages: list[dict[str, Any]],
        include_meaning_tree: bool = False,
        attachments: list[dict[str, Any]] | None = None,
        codex_sandbox: str = "danger-full-access",
    ) -> CodexRunResult:
        prompt_payload = self.prompt_payload(
            project=project,
            document_name=document_name,
            document=document,
            node_id=node_id,
            user_text=user_text,
            conversation=conversation,
            messages=messages,
            include_meaning_tree=include_meaning_tree,
            attachments=attachments,
        )
        prompt = self.render_prompt(prompt_payload)
        tool_env = {
            "ABC_CANVAS_API_BASE": os.environ.get("ABC_CANVAS_API_BASE", "http://127.0.0.1:8790"),
            "ABC_POWAN_PROJECT": project,
            "ABC_POWAN_FILE": document_name,
            "ABC_POWAN_NODE_ID": node_id,
        }
        thread_id = conversation.get("codexThreadId")
        cancel_key = self.cancel_key(project, document_name, node_id)
        if thread_id:
            result = self.run_codex(
                project_root,
                prompt,
                thread_id=str(thread_id),
                tool_env=tool_env,
                cancel_key=cancel_key,
                sandbox=codex_sandbox,
            )
            if result.returncode == 0 or result.cancelled:
                return result
            self.log_event(
                "warn",
                "codex-exec-resume-failed-new-session",
                {
                    "project": project,
                    "file": document_name,
                    "nodeId": node_id,
                    "conversationId": conversation.get("id"),
                    "threadId": thread_id,
                    "returncode": result.returncode,
                    "stderr": result.stderr[-1000:],
                },
            )
        return self.run_codex(
            project_root,
            prompt,
            thread_id=None,
            tool_env=tool_env,
            cancel_key=cancel_key,
            sandbox=codex_sandbox,
        )

    def summarize_conversation(
        self,
        *,
        project_root: Path,
        project: str,
        document_name: str,
        node_id: str,
        messages: list[dict[str, Any]],
    ) -> CodexRunResult:
        source = self.build_summary_source(messages)
        tool_env = {
            "ABC_CANVAS_API_BASE": os.environ.get("ABC_CANVAS_API_BASE", "http://127.0.0.1:8790"),
            "ABC_POWAN_PROJECT": project,
            "ABC_POWAN_FILE": document_name,
            "ABC_POWAN_NODE_ID": node_id,
        }
        max_chars = 3000
        prompt = self.render_summary_prompt(source["text"], max_chars=max_chars)
        result = self.run_codex(project_root, prompt, thread_id=None, tool_env=tool_env, ignore_rules=True)
        if result.returncode != 0 or not result.text:
            result.input_chars = source["input_chars"]
            result.turn_count = source["turn_count"]
            return result
        retry_count = 0
        trimmed_chars = 0
        if len(result.text) > max_chars:
            retry_count = 1
            retry_prompt = self.render_summary_retry_prompt(result.text, max_chars=max_chars)
            retry_result = self.run_codex(project_root, retry_prompt, thread_id=None, tool_env=tool_env, ignore_rules=True)
            if retry_result.returncode == 0 and retry_result.text:
                retry_result.stdout = f"{result.stdout}\n{retry_result.stdout}".strip()
                retry_result.stderr = f"{result.stderr}\n{retry_result.stderr}".strip()
                retry_result.duration_ms += result.duration_ms
                result = retry_result
            else:
                result.stderr = f"{result.stderr}\nsummary retry failed: {retry_result.stderr}".strip()
        if len(result.text) > max_chars:
            trimmed_chars = len(result.text) - max_chars
            result.text = result.text[:max_chars].rstrip()
        result.input_chars = source["input_chars"]
        result.turn_count = source["turn_count"]
        result.retry_count = retry_count
        result.trimmed_chars = trimmed_chars
        return result

    def run_codex(
        self,
        project_root: Path,
        prompt: str,
        thread_id: str | None,
        tool_env: dict[str, str] | None = None,
        ignore_rules: bool = False,
        cancel_key: str | None = None,
        sandbox: str = "danger-full-access",
    ) -> CodexRunResult:
        codex_command = shutil.which("codex") or shutil.which("codex.cmd") or "codex"
        output_path = Path(tempfile.gettempdir()) / f"abc_canvas_codex_{uuid4().hex}.txt"
        if thread_id:
            command = [
                codex_command,
                "exec",
                "resume",
                "--json",
                "--skip-git-repo-check",
                "-o",
                str(output_path),
                thread_id,
                "-",
            ]
            if sandbox == "danger-full-access":
                command.insert(3, "--dangerously-bypass-approvals-and-sandbox")
        else:
            command = [
                codex_command,
                "exec",
                "--json",
                "-C",
                str(project_root),
                "--skip-git-repo-check",
                "--sandbox",
                sandbox,
                "-o",
                str(output_path),
                "-",
            ]
            if ignore_rules:
                command.insert(-3, "--ignore-rules")
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        if tool_env:
            env.update(tool_env)
        start = time.monotonic()
        stdout = ""
        stderr = ""
        returncode = 127
        cancelled = False
        process: subprocess.Popen[str] | None = None
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(project_root),
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if cancel_key:
                with self.process_lock:
                    self.active_processes[cancel_key] = process
            timeout = self.timeout_seconds if self.timeout_seconds and self.timeout_seconds > 0 else None
            stdout, stderr = process.communicate(input=prompt, timeout=timeout)
            stdout = stdout or ""
            stderr = stderr or ""
            returncode = process.returncode
        except OSError as exc:
            stderr = f"Failed to start codex exec: {exc}"
            returncode = 127
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else ""
            stderr = f"{stderr}\nCodex exec timed out after {self.timeout_seconds}s".strip()
            returncode = 124
            if process:
                process.kill()
                try:
                    extra_stdout, extra_stderr = process.communicate(timeout=3)
                    stdout = f"{stdout}{extra_stdout or ''}"
                    stderr = f"{stderr}\n{extra_stderr or ''}".strip()
                except subprocess.TimeoutExpired:
                    pass
        finally:
            if cancel_key:
                with self.process_lock:
                    if process is not None and self.active_processes.get(cancel_key) is process:
                        self.active_processes.pop(cancel_key, None)
                    cancelled = cancel_key in self.cancelled_keys
                    self.cancelled_keys.discard(cancel_key)
        if cancelled:
            stderr = f"{stderr}\nCodex exec cancelled".strip()
        duration_ms = round((time.monotonic() - start) * 1000)
        text = self.read_last_message(output_path) or self.last_agent_message(stdout)
        detected_thread_id = self.thread_id_from_stdout(stdout) or thread_id
        try:
            output_path.unlink(missing_ok=True)
        except OSError:
            pass
        return CodexRunResult(
            text=text.strip(),
            thread_id=detected_thread_id,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            resumed=bool(thread_id),
            command=command,
            cancelled=cancelled,
        )

    def prompt_payload(
        self,
        *,
        project: str,
        document_name: str,
        document: dict[str, Any],
        node_id: str,
        user_text: str,
        conversation: dict[str, Any],
        messages: list[dict[str, Any]],
        include_meaning_tree: bool = False,
        attachments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return build_powan_context(
            project=project,
            document_name=document_name,
            document=document,
            node_id=node_id,
            conversation=conversation,
            messages=messages,
            user_text=user_text,
            include_meaning_tree=include_meaning_tree,
            attachments=attachments,
        )

    def render_prompt(self, payload: dict[str, Any]) -> str:
        context_json = json.dumps(payload, ensure_ascii=False, indent=2)
        return f"""あなたはポワンです。
このポワンに込められた意味として話しましょう。
返事はこのポワン本人として自然に返してください。
attachments に path がある時は、そのファイルをこのプロジェクト内の添付として読めます。
現在のポワン文脈:
```json
{context_json}
```

今回のユーザー発言:
{payload["userText"]}
"""

    def render_summary_prompt(self, source_text: str, max_chars: int) -> str:
        return f"""この会話を次のセッションへ渡すために要約する。
{int(max_chars)}文字以内に収める。
出力は要約本文だけにする。見出し、前置き、コードブロックを付けない。
古い完了済み詳細と重複を削り、未完了の依頼、決定、重要な制約、直近の状態を残す。

{source_text}
"""

    def render_summary_retry_prompt(self, source_text: str, max_chars: int) -> str:
        return f"""同じ内容を指定文字数以内の要約本文だけに短くする。見出しを付けない。
{int(max_chars)}文字以内に収める。
出力は要約本文だけにする。見出し、前置き、コードブロックを付けない。

{source_text}
"""

    def build_summary_source(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        parts: list[str] = []
        turn_count = 0
        for message in messages:
            role = str(message.get("role") or "").strip() or "unknown"
            text = self.clean_summary_block(str(message.get("text") or ""))
            if not text:
                continue
            if role == "system" and text.startswith("これまでの会話の要約:"):
                parts.append(self.clean_summary_block(text.replace("これまでの会話の要約:", "", 1)))
                continue
            parts.append(f"{role}:\n{text}")
            if role in {"user", "assistant"}:
                turn_count += 1
        source_text = "\n\n".join(part for part in parts if part).strip()
        return {
            "text": source_text,
            "input_chars": len(source_text),
            "turn_count": turn_count,
        }

    def clean_summary_block(self, text: str) -> str:
        lines = [line.rstrip() for line in text.strip().splitlines()]
        cleaned: list[str] = []
        previous_blank = False
        for line in lines:
            is_blank = not line.strip()
            if is_blank and previous_blank:
                continue
            cleaned.append(line)
            previous_blank = is_blank
        return "\n".join(cleaned).strip()

    def read_last_message(self, output_path: Path) -> str:
        if not output_path.exists():
            return ""
        try:
            return output_path.read_text(encoding="utf-8")
        except OSError:
            return ""

    def thread_id_from_stdout(self, stdout: str) -> str | None:
        for event in self.json_events(stdout):
            if event.get("type") == "thread.started" and event.get("thread_id"):
                return str(event["thread_id"])
        return None

    def last_agent_message(self, stdout: str) -> str:
        last = ""
        for event in self.json_events(stdout):
            item = event.get("item") if event.get("type") == "item.completed" else None
            if item and item.get("type") == "agent_message":
                last = str(item.get("text") or "")
        return last

    def json_events(self, stdout: str) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for line in stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict):
                events.append(event)
        return events
