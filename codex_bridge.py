from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import ctypes
import ctypes.wintypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
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
        self.active_runs: dict[str, dict[str, Any]] = {}
        self.cancelled_keys: set[str] = set()
        self.process_lock = threading.RLock()

    def cancel_key(self, project: str, document_name: str, node_id: str) -> str:
        return f"{project}\n{document_name}\n{node_id}"

    def codex_event_context(self, tool_env: dict[str, str] | None) -> dict[str, str]:
        if not tool_env:
            return {}
        return {
            "project": tool_env.get("ABC_POWAN_PROJECT", ""),
            "file": tool_env.get("ABC_POWAN_FILE", ""),
            "nodeId": tool_env.get("ABC_POWAN_NODE_ID", ""),
        }

    def terminate_process_tree(self, process: subprocess.Popen[str]) -> dict[str, Any]:
        pid = process.pid
        if process.poll() is not None:
            return {"pid": pid, "alreadyExited": True, "treeKill": False}
        if os.name == "nt":
            command = ["taskkill", "/PID", str(pid), "/T", "/F"]
            try:
                result = subprocess.run(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=10,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                fallback_kill = False
                fallback_error = ""
                if result.returncode != 0:
                    time.sleep(0.2)
                    if process.poll() is None:
                        try:
                            process.kill()
                            fallback_kill = True
                        except OSError as exc:
                            fallback_error = str(exc)
                return {
                    "pid": pid,
                    "treeKill": True,
                    "taskkillReturncode": result.returncode,
                    "taskkillStdout": (result.stdout or "")[-1000:],
                    "taskkillStderr": (result.stderr or "")[-1000:],
                    "fallbackKill": fallback_kill,
                    "fallbackError": fallback_error,
                }
            except (OSError, subprocess.TimeoutExpired) as exc:
                fallback_error = ""
                try:
                    process.kill()
                except OSError as kill_exc:
                    fallback_error = str(kill_exc)
                return {
                    "pid": pid,
                    "treeKill": False,
                    "fallbackKill": True,
                    "error": str(exc),
                    "fallbackError": fallback_error,
                }
        process.terminate()
        return {"pid": pid, "treeKill": False, "terminated": True}

    def cancel(self, *, project: str, document_name: str, node_id: str) -> dict[str, Any]:
        key = self.cancel_key(project, document_name, node_id)
        with self.process_lock:
            process = self.active_processes.get(key)
            if not process or process.poll() is not None:
                return {"cancelled": False, "running": False}
            self.cancelled_keys.add(key)
            pid = process.pid
        try:
            kill_info = self.terminate_process_tree(process)
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
            {"project": project, "file": document_name, "nodeId": node_id, **kill_info},
        )
        return {"cancelled": True, "running": True, **kill_info}

    def begin_active_run(
        self,
        *,
        project: str,
        document_name: str,
        node_id: str,
        run_id: int | None,
    ) -> bool:
        if run_id is None:
            return True
        key = self.cancel_key(project, document_name, node_id)
        with self.process_lock:
            existing = self.active_runs.get(key)
            if (
                existing
                and existing.get("runId") != int(run_id)
            ):
                return False
            self.active_runs[key] = {
                "runId": int(run_id),
                "project": project,
                "documentName": document_name,
                "nodeId": node_id,
                "pid": None,
                "startedAt": time.monotonic(),
            }
        return True

    def active_run_conflicts(
        self,
        *,
        project: str,
        document_name: str,
        node_id: str,
        run_id: int | None,
    ) -> bool:
        if run_id is None:
            return False
        key = self.cancel_key(project, document_name, node_id)
        with self.process_lock:
            active = self.active_runs.get(key)
            return bool(active and active.get("runId") != int(run_id))

    def end_active_run(
        self,
        *,
        project: str,
        document_name: str,
        node_id: str,
        run_id: int | None,
    ) -> None:
        if run_id is None:
            return
        key = self.cancel_key(project, document_name, node_id)
        with self.process_lock:
            active = self.active_runs.get(key)
            if active and active.get("runId") == int(run_id):
                self.active_runs.pop(key, None)

    def mark_active_run_process(
        self,
        *,
        project: str,
        document_name: str,
        node_id: str,
        run_id: int | None,
        pid: int,
    ) -> None:
        if run_id is None:
            return
        key = self.cancel_key(project, document_name, node_id)
        with self.process_lock:
            active = self.active_runs.get(key)
            if active and active.get("runId") == int(run_id):
                active["pid"] = int(pid)

    def is_agent_run_active(
        self,
        *,
        project: str,
        document_name: str,
        node_id: str,
        run_id: int | None,
    ) -> bool:
        if run_id is None:
            return False
        key = self.cancel_key(project, document_name, node_id)
        with self.process_lock:
            active = self.active_runs.get(key)
            if not active or active.get("runId") != int(run_id):
                return False
            process = self.active_processes.get(key)
            if process is not None and process.poll() is not None:
                self.active_processes.pop(key, None)
            return True

    def active_run_info(
        self,
        *,
        project: str,
        document_name: str,
        node_id: str,
        run_id: int | None,
    ) -> dict[str, Any] | None:
        if run_id is None:
            return None
        key = self.cancel_key(project, document_name, node_id)
        with self.process_lock:
            active = self.active_runs.get(key)
            if not active or active.get("runId") != int(run_id):
                return None
            process = self.active_processes.get(key)
            process_running = False
            pid = active.get("pid")
            if process is not None:
                process_running = process.poll() is None
                pid = process.pid
            return {
                "runId": int(run_id),
                "pid": pid,
                "processRunning": process_running,
            }

    def is_pid_running(self, pid: int | None) -> bool:
        if not pid or int(pid) <= 0:
            return False
        clean_pid = int(pid)
        if os.name == "nt":
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            process_query_limited_information = 0x1000
            still_active = 259
            kernel32.OpenProcess.argtypes = [ctypes.wintypes.DWORD, ctypes.wintypes.BOOL, ctypes.wintypes.DWORD]
            kernel32.OpenProcess.restype = ctypes.wintypes.HANDLE
            kernel32.GetExitCodeProcess.argtypes = [ctypes.wintypes.HANDLE, ctypes.POINTER(ctypes.wintypes.DWORD)]
            kernel32.GetExitCodeProcess.restype = ctypes.wintypes.BOOL
            kernel32.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]
            kernel32.CloseHandle.restype = ctypes.wintypes.BOOL
            handle = kernel32.OpenProcess(process_query_limited_information, False, clean_pid)
            if not handle:
                return False
            try:
                exit_code = ctypes.wintypes.DWORD()
                if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    return False
                return int(exit_code.value) == still_active
            finally:
                kernel32.CloseHandle(handle)
        try:
            os.kill(clean_pid, 0)
        except OSError:
            return False
        return True

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
        incoming_message: dict[str, Any] | None = None,
        include_meaning_tree: bool = False,
        include_direct_child_code: bool = False,
        attachments: list[dict[str, Any]] | None = None,
        codex_sandbox: str = "danger-full-access",
        codex_model: str = "",
        codex_reasoning_effort: str = "",
        agent_run_id: int | None = None,
        on_process_started: Callable[[int], None] | None = None,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ) -> CodexRunResult:
        prompt_payload = self.prompt_payload(
            project=project,
            document_name=document_name,
            document=document,
            node_id=node_id,
            user_text=user_text,
            conversation=conversation,
            messages=messages,
            incoming_message=incoming_message,
            include_meaning_tree=include_meaning_tree,
            include_direct_child_code=include_direct_child_code,
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
        if self.active_run_conflicts(
            project=project,
            document_name=document_name,
            node_id=node_id,
            run_id=agent_run_id,
        ):
            return CodexRunResult(
                text="",
                thread_id=str(thread_id) if thread_id else None,
                returncode=409,
                stdout="",
                stderr="Codex exec already running for this powan",
                duration_ms=0,
                resumed=bool(thread_id),
                command=[],
            )
        if not self.begin_active_run(project=project, document_name=document_name, node_id=node_id, run_id=agent_run_id):
            return CodexRunResult(
                text="",
                thread_id=str(thread_id) if thread_id else None,
                returncode=409,
                stdout="",
                stderr="Codex exec already running for this powan",
                duration_ms=0,
                resumed=bool(thread_id),
                command=[],
            )
        try:
            if thread_id:
                result = self.run_codex(
                    project_root,
                    prompt,
                    thread_id=str(thread_id),
                    tool_env=tool_env,
                    cancel_key=cancel_key,
                    sandbox=codex_sandbox,
                    model=codex_model,
                    reasoning_effort=codex_reasoning_effort,
                    agent_run_id=agent_run_id,
                    on_process_started=on_process_started,
                    on_event=on_event,
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
                model=codex_model,
                reasoning_effort=codex_reasoning_effort,
                agent_run_id=agent_run_id,
                on_process_started=on_process_started,
                on_event=on_event,
            )
        finally:
            self.end_active_run(project=project, document_name=document_name, node_id=node_id, run_id=agent_run_id)

    def summarize_conversation(
        self,
        *,
        project_root: Path,
        project: str,
        document_name: str,
        node_id: str,
        messages: list[dict[str, Any]],
        codex_model: str = "",
        codex_reasoning_effort: str = "",
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
        result = self.run_codex(
            project_root,
            prompt,
            thread_id=None,
            tool_env=tool_env,
            ignore_rules=True,
            model=codex_model,
            reasoning_effort=codex_reasoning_effort,
        )
        if result.returncode != 0 or not result.text:
            result.input_chars = source["input_chars"]
            result.turn_count = source["turn_count"]
            return result
        retry_count = 0
        trimmed_chars = 0
        if len(result.text) > max_chars:
            retry_count = 1
            retry_prompt = self.render_summary_retry_prompt(result.text, max_chars=max_chars)
            retry_result = self.run_codex(
                project_root,
                retry_prompt,
                thread_id=None,
                tool_env=tool_env,
                ignore_rules=True,
                model=codex_model,
                reasoning_effort=codex_reasoning_effort,
            )
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
        model: str = "",
        reasoning_effort: str = "",
        agent_run_id: int | None = None,
        on_process_started: Callable[[int], None] | None = None,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ) -> CodexRunResult:
        codex_command = shutil.which("codex.cmd") or shutil.which("codex.exe") or shutil.which("codex") or "codex"
        output_path = Path(tempfile.gettempdir()) / f"abc_canvas_codex_{uuid4().hex}.txt"
        option_args = self.codex_option_args(model=model, reasoning_effort=reasoning_effort)
        project_root_uri = project_root.resolve().as_uri()
        if thread_id:
            command = [
                codex_command,
                "exec",
                "resume",
                "--json",
                *option_args,
                "-c",
                f'sandboxCwd="{project_root_uri}"',
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
                *option_args,
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
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []
        output_lock = threading.RLock()
        returncode = 127
        cancelled = False
        process: subprocess.Popen[str] | None = None
        if cancel_key:
            with self.process_lock:
                active_process = self.active_processes.get(cancel_key)
                if active_process and active_process.poll() is None:
                    stderr = "Codex exec already running for this powan"
                    return CodexRunResult(
                        text="",
                        thread_id=thread_id,
                        returncode=409,
                        stdout="",
                        stderr=stderr,
                        duration_ms=0,
                        resumed=bool(thread_id),
                        command=command,
                    )
                if active_process and active_process.poll() is not None:
                    self.active_processes.pop(cancel_key, None)
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
            self.log_event(
                "info",
                "codex-exec-process-started",
                {
                    **self.codex_event_context(tool_env),
                    "pid": process.pid,
                    "cwd": str(project_root),
                    "resumed": bool(thread_id),
                    "sandbox": sandbox,
                    "model": model,
                    "reasoningEffort": reasoning_effort,
                },
            )
            if cancel_key:
                with self.process_lock:
                    self.active_processes[cancel_key] = process
            context = self.codex_event_context(tool_env)
            self.mark_active_run_process(
                project=context.get("project", ""),
                document_name=context.get("file", ""),
                node_id=context.get("nodeId", ""),
                run_id=agent_run_id,
                pid=process.pid,
            )
            if on_process_started is not None:
                on_process_started(process.pid)
            timeout = self.timeout_seconds if self.timeout_seconds and self.timeout_seconds > 0 else None
            if process.stdin is not None:
                process.stdin.write(prompt)
                process.stdin.close()

            def read_stdout() -> None:
                if process is None or process.stdout is None:
                    return
                for line in process.stdout:
                    with output_lock:
                        stdout_lines.append(line)
                    self.handle_codex_stdout_line(line, tool_env=tool_env, on_event=on_event)

            def read_stderr() -> None:
                if process is None or process.stderr is None:
                    return
                for line in process.stderr:
                    with output_lock:
                        stderr_lines.append(line)

            stdout_thread = threading.Thread(target=read_stdout, name="abc-codex-stdout", daemon=True)
            stderr_thread = threading.Thread(target=read_stderr, name="abc-codex-stderr", daemon=True)
            stdout_thread.start()
            stderr_thread.start()
            process.wait(timeout=timeout)
            stdout_thread.join(timeout=5)
            stderr_thread.join(timeout=5)
            with output_lock:
                stdout = "".join(stdout_lines)
                stderr = "".join(stderr_lines)
            returncode = process.returncode
        except OSError as exc:
            stderr = f"Failed to start codex exec: {exc}"
            returncode = 127
        except subprocess.TimeoutExpired as exc:
            with output_lock:
                stdout = "".join(stdout_lines)
                stderr = "".join(stderr_lines)
            stderr = f"{stderr}\nCodex exec timed out after {self.timeout_seconds}s".strip()
            returncode = 124
            if process:
                kill_info = self.terminate_process_tree(process)
                self.log_event(
                    "warn",
                    "codex-exec-timeout-kill",
                    {
                        **self.codex_event_context(tool_env),
                        **kill_info,
                        "timeoutSeconds": self.timeout_seconds,
                    },
                )
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    pass
                with output_lock:
                    stdout = "".join(stdout_lines)
                    stderr = f"{stderr}\n{''.join(stderr_lines)}".strip()
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

    def handle_codex_stdout_line(
        self,
        line: str,
        *,
        tool_env: dict[str, str] | None,
        on_event: Callable[[dict[str, Any]], None] | None,
    ) -> None:
        clean_line = str(line or "").rstrip("\r\n")
        if not clean_line:
            return
        try:
            event = json.loads(clean_line)
        except json.JSONDecodeError:
            self.log_event(
                "debug",
                "codex-exec-non-json-stdout",
                {
                    **self.codex_event_context(tool_env),
                    "linePreview": clean_line[:500],
                },
            )
            return
        if not isinstance(event, dict):
            return
        self.log_event(
            "trace",
            "codex-exec-json-event",
            {
                **self.codex_event_context(tool_env),
                "type": str(event.get("type") or ""),
                "itemType": str((event.get("item") or {}).get("type") or "") if isinstance(event.get("item"), dict) else "",
            },
        )
        if on_event is not None:
            try:
                on_event(event)
            except Exception as exc:
                self.log_event(
                    "warn",
                    "codex-exec-event-callback-failed",
                    {
                        **self.codex_event_context(tool_env),
                        "type": str(event.get("type") or ""),
                        "error": repr(exc),
                    },
                )

    def codex_option_args(self, *, model: str = "", reasoning_effort: str = "") -> list[str]:
        args: list[str] = []
        clean_model = str(model or "").strip()
        if clean_model:
            args.extend(["-m", clean_model])
        clean_effort = str(reasoning_effort or "").strip().lower()
        if clean_effort:
            args.extend(["-c", f'model_reasoning_effort="{clean_effort}"'])
        return args

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
        incoming_message: dict[str, Any] | None = None,
        include_meaning_tree: bool = False,
        include_direct_child_code: bool = False,
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
            incoming_message=incoming_message,
            include_meaning_tree=include_meaning_tree,
            include_direct_child_code=include_direct_child_code,
            attachments=attachments,
        )

    def render_prompt(self, payload: dict[str, Any]) -> str:
        context_json = json.dumps(payload, ensure_ascii=False, indent=2)
        code_instruction = ""
        if payload.get("codeWriteMode"):
            code_instruction = "今回は自分のコードを書くための送信です。directChildCode に入っている直下ポワンのコードを先に読んで、それを材料にしてください。\n"
        return f"""あなたはポワンです。
このポワンに込められた意味として話しましょう。
返事はこのポワン本人として自然に返してください。
attachments に path がある時は、そのファイルをこのプロジェクト内の添付として読めます。
今回の入力は context.incomingMessage を正として扱ってください。
context.userText は古い互換フィールドです。誰から来たか、入力種別、実行範囲は incomingMessage を見てください。
incomingMessage.allowedAction が read_only の時は、返答内容の確認と要約だけを行ってください。
{code_instruction}現在のポワン文脈:
```json
{context_json}
```

今回の入力本文（互換表示）:
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
