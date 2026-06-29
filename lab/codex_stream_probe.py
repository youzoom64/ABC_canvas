from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
LOG_ROOT = ROOT / "logs"


def now_stamp() -> str:
    return datetime.now().isoformat(timespec="milliseconds")


def run_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def write_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def compact(value: Any, limit: int = 500) -> str:
    text = str(value or "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if len(text) <= limit:
        return text
    return text[:limit] + f"... <trimmed {len(text) - limit} chars>"


def codex_executable() -> str:
    if os.name == "nt":
        for name in ("codex.cmd", "codex.exe", "codex.ps1"):
            path = shutil.which(name)
            if path:
                return path
    path = shutil.which("codex")
    if path:
        return path
    return "codex"


def summarize_event(event: dict[str, Any]) -> dict[str, Any]:
    event_type = str(event.get("type") or event.get("event") or event.get("msg", "") or "unknown")
    summary: dict[str, Any] = {
        "type": event_type,
        "keys": sorted(str(key) for key in event.keys()),
    }
    for key in (
        "id",
        "msg",
        "message",
        "role",
        "status",
        "item_type",
        "call_id",
        "name",
        "command",
        "cwd",
        "exit_code",
        "duration_ms",
        "session_id",
        "thread_id",
    ):
        if key in event:
            summary[key] = event[key]
    if "item" in event and isinstance(event["item"], dict):
        item = event["item"]
        summary["itemKeys"] = sorted(str(key) for key in item.keys())
        for key in ("type", "role", "status", "call_id", "name", "command", "arguments"):
            if key in item:
                summary[f"item.{key}"] = item[key]
    if "delta" in event:
        summary["deltaPreview"] = compact(event.get("delta"), 300)
    if "text" in event:
        summary["textPreview"] = compact(event.get("text"), 300)
    if "content" in event:
        summary["contentPreview"] = compact(event.get("content"), 300)
    return summary


def stderr_reader(process: subprocess.Popen[str], stderr_path: Path, parsed_path: Path) -> None:
    assert process.stderr is not None
    for line in process.stderr:
        record = {"at": now_stamp(), "stream": "stderr", "line": line.rstrip("\n")}
        write_jsonl(stderr_path, record)
        write_jsonl(parsed_path, {"at": now_stamp(), "stream": "stderr", "preview": compact(line, 500)})


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe codex exec --json streaming behavior.")
    parser.add_argument("--prompt", default="", help="Prompt to send to codex. A default probe prompt is used when empty.")
    parser.add_argument("--model", default=os.environ.get("CODEX_PROBE_MODEL", ""), help="Optional Codex model.")
    parser.add_argument("--sandbox", default="workspace-write", choices=["read-only", "workspace-write", "danger-full-access"])
    parser.add_argument("--timeout", type=float, default=180.0)
    args = parser.parse_args()

    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    rid = run_id()
    run_dir = LOG_ROOT / rid
    run_dir.mkdir(parents=True, exist_ok=True)
    raw_stdout_path = run_dir / "stdout.raw.jsonl"
    parsed_path = run_dir / "events.parsed.jsonl"
    stderr_path = run_dir / "stderr.jsonl"
    last_message_path = run_dir / "last_message.txt"
    summary_path = run_dir / "summary.json"

    prompt = args.prompt.strip() or (
        "これはABC Canvasとは無関係なCodex JSONストリーム観察テストです。\n"
        "短い作業をしてください。\n"
        "1. 現在の作業ディレクトリを確認してください。\n"
        "2. lab_probe_note.txt に1行だけ書いてください。\n"
        "3. そのファイルを読んでください。\n"
        "4. 最後に、何をしたかを2行以内で返してください。\n"
    )

    command = [
        codex_executable(),
        "exec",
        "--json",
        "--skip-git-repo-check",
        "--cd",
        str(ROOT),
        "--sandbox",
        args.sandbox,
        "-o",
        str(last_message_path),
    ]
    if args.model.strip():
        command.extend(["--model", args.model.strip()])
    command.append("-")

    start = time.monotonic()
    metadata = {
        "at": now_stamp(),
        "runId": rid,
        "root": str(ROOT),
        "command": command,
        "prompt": prompt,
        "timeout": args.timeout,
    }
    write_jsonl(parsed_path, {"at": now_stamp(), "stream": "probe", "event": "start", **metadata})

    process = subprocess.Popen(
        command,
        cwd=str(ROOT),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    process.stdin.write(prompt)
    process.stdin.close()

    stderr_thread = threading.Thread(target=stderr_reader, args=(process, stderr_path, parsed_path), daemon=True)
    stderr_thread.start()

    event_counts: dict[str, int] = {}
    line_count = 0
    non_json_lines = 0
    timed_out = False

    while True:
        if args.timeout > 0 and time.monotonic() - start > args.timeout:
            timed_out = True
            process.kill()
            write_jsonl(parsed_path, {"at": now_stamp(), "stream": "probe", "event": "timeout", "timeout": args.timeout})
            break
        line = process.stdout.readline()
        if line:
            line_count += 1
            raw_record = {"at": now_stamp(), "lineNumber": line_count, "line": line.rstrip("\n")}
            write_jsonl(raw_stdout_path, raw_record)
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                non_json_lines += 1
                write_jsonl(
                    parsed_path,
                    {
                        "at": now_stamp(),
                        "stream": "stdout",
                        "lineNumber": line_count,
                        "kind": "non_json_stdout",
                        "parseError": str(exc),
                        "linePreview": compact(line, 1000),
                    },
                )
                continue
            summary = summarize_event(event)
            event_type = str(summary.get("type") or "unknown")
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
            write_jsonl(
                parsed_path,
                {
                    "at": now_stamp(),
                    "stream": "stdout",
                    "lineNumber": line_count,
                    "summary": summary,
                    "event": event,
                },
            )
            continue
        if process.poll() is not None:
            break
        time.sleep(0.02)

    stderr_thread.join(timeout=2)
    duration_ms = int((time.monotonic() - start) * 1000)
    last_message = last_message_path.read_text(encoding="utf-8") if last_message_path.exists() else ""
    summary = {
        "runId": rid,
        "startedAt": metadata["at"],
        "finishedAt": now_stamp(),
        "durationMs": duration_ms,
        "returncode": process.returncode,
        "timedOut": timed_out,
        "lineCount": line_count,
        "nonJsonStdoutLines": non_json_lines,
        "eventCounts": event_counts,
        "paths": {
            "runDir": str(run_dir),
            "stdoutRaw": str(raw_stdout_path),
            "eventsParsed": str(parsed_path),
            "stderr": str(stderr_path),
            "lastMessage": str(last_message_path),
            "summary": str(summary_path),
        },
        "lastMessagePreview": compact(last_message, 1000),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return int(process.returncode or 0)


if __name__ == "__main__":
    raise SystemExit(main())
