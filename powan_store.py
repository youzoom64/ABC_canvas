from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterator

from fastapi import HTTPException

from project_scaffold import ensure_project_scaffold


BlankDocumentFn = Callable[[], dict[str, Any]]
LogFn = Callable[[str, str, dict[str, Any] | None], None]
WORKSPACE_SIZE = 10000
WORKSPACE_ORIGIN_X = 5000
WORKSPACE_ORIGIN_Y = 5000
DEFAULT_NODE_WIDTH = 280
DEFAULT_NODE_HEIGHT = 160
CODEX_DISCONNECTED_SYSTEM_MESSAGE = "Codexが切断されました。返事は戻りません。"


class PowanStore:
    def __init__(
        self,
        work_root: Path,
        default_file: str,
        blank_document: BlankDocumentFn,
        log_event: LogFn,
    ) -> None:
        self.work_root = work_root
        self.default_file = default_file
        self.blank_document = blank_document
        self.log_event = log_event

    def safe_project_name(self, name: str) -> str:
        candidate = name.strip()
        if not candidate:
            raise HTTPException(status_code=400, detail="Project name is required")
        if Path(candidate).name != candidate or any(part in candidate for part in ("/", "\\")):
            raise HTTPException(status_code=400, detail="Invalid project name")
        if candidate in {".", ".."} or any(char in '<>:"|?*' or ord(char) < 32 for char in candidate):
            raise HTTPException(status_code=400, detail="Invalid project name")
        return candidate

    def safe_powan_name(self, name: str | None = None) -> str:
        safe_name = Path(name or self.default_file).name
        if not safe_name.endswith(".powan"):
            safe_name += ".powan"
        if safe_name in {".powan", "..powan"}:
            raise HTTPException(status_code=400, detail="Invalid powan file name")
        return safe_name

    def project_root(self, project: str) -> Path:
        root = (self.work_root / self.safe_project_name(project)).resolve()
        work_root = self.work_root.resolve()
        if work_root not in root.parents and root != work_root:
            raise HTTPException(status_code=400, detail="Invalid project path")
        return root

    def powan_path(self, project: str, name: str | None = None) -> Path:
        root = self.project_root(project)
        path = (root / self.safe_powan_name(name)).resolve()
        if root not in path.parents and path != root:
            raise HTTPException(status_code=400, detail="Invalid file path")
        return path

    def db_path(self, project: str) -> Path:
        return self.project_root(project) / "powan.db"

    def connect(self, project: str) -> sqlite3.Connection:
        root = self.project_root(project)
        root.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(root / "powan.db", timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        self.ensure_schema(connection)
        return connection

    @contextmanager
    def session(self, project: str) -> Iterator[sqlite3.Connection]:
        connection = self.connect(project)
        try:
            yield connection
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()
        finally:
            connection.close()

    def _write_document_export(self, project: str, document_name: str, document: dict[str, Any]) -> None:
        self.powan_path(project, document_name).write_text(
            json.dumps(document, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _preserve_server_node_state(
        self,
        connection: sqlite3.Connection,
        document_name: str,
        document: dict[str, Any],
    ) -> None:
        row = connection.execute(
            "SELECT document_json FROM documents WHERE name = ?",
            (document_name,),
        ).fetchone()
        if row is None:
            for node in document.get("nodes") or []:
                node.pop("codexState", None)
            return
        try:
            current_document = json.loads(str(row["document_json"]))
        except json.JSONDecodeError:
            return
        current_nodes = {
            str(node.get("id") or ""): node
            for node in current_document.get("nodes") or []
            if str(node.get("id") or "")
        }
        for node in document.get("nodes") or []:
            current_state = current_nodes.get(str(node.get("id") or ""), {}).get("codexState")
            if isinstance(current_state, dict) and current_state:
                node["codexState"] = current_state
            else:
                node.pop("codexState", None)

    def _set_powan_codex_state(
        self,
        connection: sqlite3.Connection,
        document_name: str,
        powan_id: str,
        codex_state_patch: dict[str, Any] | None,
        now: str,
    ) -> dict[str, Any] | None:
        row = connection.execute(
            "SELECT document_json FROM documents WHERE name = ?",
            (document_name,),
        ).fetchone()
        if row is None:
            return None
        try:
            document = json.loads(str(row["document_json"]))
        except json.JSONDecodeError:
            return None
        target_node: dict[str, Any] | None = None
        for node in document.get("nodes") or []:
            if str(node.get("id") or "") == str(powan_id):
                target_node = node
                break
        if target_node is None:
            return None

        if codex_state_patch is None:
            state = target_node.get("codexState")
            if not isinstance(state, dict) or not state.get("disconnected"):
                return None
            state.pop("disconnected", None)
            state.pop("disconnectedAt", None)
            state.pop("disconnectedReason", None)
            state.pop("disconnectedMessage", None)
            if state:
                target_node["codexState"] = state
            else:
                target_node.pop("codexState", None)
        else:
            state = target_node.get("codexState")
            if not isinstance(state, dict):
                state = {}
            state.update(codex_state_patch)
            target_node["codexState"] = state

        connection.execute(
            """
            UPDATE documents
            SET document_json = ?, updated_at = ?
            WHERE name = ?
            """,
            (
                json.dumps(document, ensure_ascii=False, separators=(",", ":")),
                now,
                document_name,
            ),
        )
        connection.execute(
            """
            UPDATE powans
            SET raw_json = ?, updated_at = ?
            WHERE document_name = ? AND id = ?
            """,
            (
                json.dumps(target_node, ensure_ascii=False, separators=(",", ":")),
                now,
                document_name,
                str(powan_id),
            ),
        )
        return document

    def mark_powan_codex_disconnected(
        self,
        project: str,
        document_name: str,
        powan_id: str,
        *,
        conversation_id: int | None = None,
        reason: str = "codex-disconnected",
        message: str = CODEX_DISCONNECTED_SYSTEM_MESSAGE,
    ) -> dict[str, Any]:
        document_name = self.safe_powan_name(document_name)
        now = datetime.now().isoformat(timespec="milliseconds")
        document_to_export: dict[str, Any] | None = None
        system_message_id: int | None = None
        with self.session(project) as connection:
            document_to_export = self._set_powan_codex_state(
                connection,
                document_name,
                powan_id,
                {
                    "disconnected": True,
                    "disconnectedAt": now,
                    "disconnectedReason": reason,
                    "disconnectedMessage": message,
                },
                now,
            )
            if conversation_id is not None:
                row = connection.execute(
                    """
                    SELECT id FROM conversations
                    WHERE id = ? AND document_name = ? AND powan_id = ?
                    """,
                    (int(conversation_id), document_name, powan_id),
                ).fetchone()
                if row is not None:
                    cursor = connection.execute(
                        """
                        INSERT INTO conversation_messages(conversation_id, role, text, created_at)
                        VALUES (?, 'system', ?, ?)
                        """,
                        (int(conversation_id), message, now),
                    )
                    system_message_id = int(cursor.lastrowid)
                    connection.execute(
                        "UPDATE conversations SET updated_at = ? WHERE id = ?",
                        (now, int(conversation_id)),
                    )
        if document_to_export is not None:
            self._write_document_export(project, document_name, document_to_export)
        self.log_event(
            "warn",
            "powan-db-mark-codex-disconnected",
            {
                "project": self.safe_project_name(project),
                "file": document_name,
                "nodeId": powan_id,
                "conversationId": conversation_id,
                "messageId": system_message_id,
                "reason": reason,
            },
        )
        return {
            "powanId": powan_id,
            "conversationId": conversation_id,
            "messageId": system_message_id,
            "reason": reason,
        }

    def clear_powan_codex_disconnected(self, project: str, document_name: str, powan_id: str) -> bool:
        document_name = self.safe_powan_name(document_name)
        now = datetime.now().isoformat(timespec="milliseconds")
        with self.session(project) as connection:
            document_to_export = self._set_powan_codex_state(connection, document_name, powan_id, None, now)
        if document_to_export is None:
            return False
        self._write_document_export(project, document_name, document_to_export)
        self.log_event(
            "info",
            "powan-db-clear-codex-disconnected",
            {
                "project": self.safe_project_name(project),
                "file": document_name,
                "nodeId": powan_id,
            },
        )
        return True

    def recover_interrupted_work(self, project: str | None = None, reason: str = "startup-recovery") -> dict[str, Any]:
        projects = [self.safe_project_name(project)] if project else [
            path.name
            for path in self.work_root.iterdir()
            if path.is_dir() and (path / "powan.db").is_file()
        ]
        now = datetime.now().isoformat(timespec="milliseconds")
        error_text = (
            "前回のサーバープロセス終了または再起動で、この作業を受け取る実行プロセスが消えました。"
            "DB上の作業中状態だけが残っていたため失敗扱いに回収しました。"
        )
        summary: dict[str, Any] = {
            "projectCount": 0,
            "agentRunCount": 0,
            "dispatchCount": 0,
            "sessionCount": 0,
            "projects": [],
        }

        for project_name in projects:
            disconnected_marks: dict[tuple[str, str, int | None], dict[str, Any]] = {}
            try:
                with self.session(project_name) as connection:
                    running_runs = connection.execute(
                        """
                        SELECT ar.id, ar.conversation_id, ar.powan_id, c.document_name
                        FROM agent_runs ar
                        LEFT JOIN conversations c ON c.id = ar.conversation_id
                        WHERE ar.status = 'running'
                        """
                    ).fetchall()
                    for row in running_runs:
                        connection.execute(
                            """
                            UPDATE agent_runs
                            SET status = 'failed',
                                error_text = CASE
                                  WHEN COALESCE(error_text, '') = '' THEN ?
                                  ELSE error_text || char(10) || ?
                                END,
                                updated_at = ?
                            WHERE id = ?
                            """,
                            (error_text, error_text, now, int(row["id"])),
                        )
                        document_name = str(row["document_name"] or self.default_file)
                        powan_id = str(row["powan_id"] or "")
                        if powan_id:
                            conversation_id = int(row["conversation_id"]) if row["conversation_id"] is not None else None
                            disconnected_marks[(document_name, powan_id, conversation_id)] = {
                                "documentName": document_name,
                                "powanId": powan_id,
                                "conversationId": conversation_id,
                            }

                    active_dispatches = connection.execute(
                        """
                        SELECT id, session_id, document_name, parent_id, child_id, conversation_id, error_text
                        FROM child_command_dispatches
                        WHERE status NOT IN ('completed', 'failed', 'cancelled', 'skipped')
                        """
                    ).fetchall()
                    for row in active_dispatches:
                        existing_error = str(row["error_text"] or "").strip()
                        next_error = error_text if not existing_error else f"{existing_error}\n{error_text}"
                        dispatch_id = int(row["id"])
                        connection.execute(
                            """
                            UPDATE child_command_dispatches
                            SET status = 'failed',
                                error_text = ?,
                                replied_at = COALESCE(replied_at, ?),
                                updated_at = ?
                            WHERE id = ?
                            """,
                            (next_error, now, now, dispatch_id),
                        )
                        connection.execute(
                            """
                            INSERT INTO child_command_events(
                              session_id, dispatch_id, document_name, parent_id, child_id,
                              event_type, payload_json, created_at
                            )
                            VALUES (?, ?, ?, ?, ?, 'recovered-failed', ?, ?)
                            """,
                            (
                                row["session_id"],
                                dispatch_id,
                                row["document_name"],
                                row["parent_id"],
                                row["child_id"],
                                json.dumps(
                                    {
                                        "status": "failed",
                                        "reason": reason,
                                        "error": error_text,
                                    },
                                    ensure_ascii=False,
                                    separators=(",", ":"),
                                ),
                                now,
                            ),
                        )
                        child_id = str(row["child_id"] or "")
                        if child_id:
                            conversation_id = int(row["conversation_id"]) if row["conversation_id"] is not None else None
                            disconnected_marks[(str(row["document_name"]), child_id, conversation_id)] = {
                                "documentName": str(row["document_name"]),
                                "powanId": child_id,
                                "conversationId": conversation_id,
                            }

                    active_sessions = connection.execute(
                        """
                        SELECT id, document_name, parent_id
                        FROM child_command_sessions
                        WHERE status NOT IN ('completed', 'failed', 'cancelled')
                        """
                    ).fetchall()
                    for row in active_sessions:
                        connection.execute(
                            """
                            UPDATE child_command_sessions
                            SET status = 'failed',
                                updated_at = ?,
                                completed_at = COALESCE(completed_at, ?)
                            WHERE document_name = ? AND id = ?
                            """,
                            (now, now, row["document_name"], row["id"]),
                        )
                        connection.execute(
                            """
                            INSERT INTO child_command_events(
                              session_id, dispatch_id, document_name, parent_id, child_id,
                              event_type, payload_json, created_at
                            )
                            VALUES (?, NULL, ?, ?, NULL, 'session-recovered-failed', ?, ?)
                            """,
                            (
                                row["id"],
                                row["document_name"],
                                row["parent_id"],
                                json.dumps(
                                    {
                                        "status": "failed",
                                        "reason": reason,
                                        "error": error_text,
                                    },
                                    ensure_ascii=False,
                                    separators=(",", ":"),
                                ),
                                now,
                            ),
                        )

                project_summary = {
                    "project": project_name,
                    "agentRunCount": len(running_runs),
                    "dispatchCount": len(active_dispatches),
                    "sessionCount": len(active_sessions),
                }
                if any(project_summary[key] for key in ("agentRunCount", "dispatchCount", "sessionCount")):
                    summary["projects"].append(project_summary)
                    summary["projectCount"] += 1
                    summary["agentRunCount"] += len(running_runs)
                    summary["dispatchCount"] += len(active_dispatches)
                    summary["sessionCount"] += len(active_sessions)
                for mark in disconnected_marks.values():
                    self.mark_powan_codex_disconnected(
                        project_name,
                        mark["documentName"],
                        mark["powanId"],
                        conversation_id=mark["conversationId"],
                        reason=reason,
                    )
            except Exception as exc:
                self.log_event(
                    "error",
                    "powan-db-recover-interrupted-work-project-failed",
                    {
                        "project": project_name,
                        "reason": reason,
                        "error": repr(exc),
                    },
                )

        if summary["agentRunCount"] or summary["dispatchCount"] or summary["sessionCount"]:
            self.log_event("warn", "powan-db-recover-interrupted-work", {**summary, "reason": reason})
        return summary

    def ensure_schema(self, connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_meta (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS documents (
              name TEXT PRIMARY KEY,
              document_json TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS powans (
              document_name TEXT NOT NULL,
              id TEXT NOT NULL,
              title TEXT NOT NULL DEFAULT '',
              body TEXT NOT NULL DEFAULT '',
              code TEXT NOT NULL DEFAULT '',
              code_language TEXT,
              parent_id TEXT,
              style_json TEXT NOT NULL DEFAULT '{}',
              layout_json TEXT NOT NULL DEFAULT '{}',
              nested_layout_json TEXT NOT NULL DEFAULT '{}',
              raw_json TEXT NOT NULL DEFAULT '{}',
              updated_at TEXT NOT NULL,
              PRIMARY KEY (document_name, id)
            );

            CREATE TABLE IF NOT EXISTS powan_edges (
              document_name TEXT NOT NULL,
              parent_id TEXT NOT NULL,
              child_id TEXT NOT NULL,
              sort_order INTEGER NOT NULL DEFAULT 0,
              PRIMARY KEY (document_name, parent_id, child_id)
            );

            CREATE TABLE IF NOT EXISTS project_settings (
              key TEXT PRIMARY KEY,
              value_json TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS conversations (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              document_name TEXT NOT NULL,
              powan_id TEXT NOT NULL,
              title TEXT NOT NULL DEFAULT '',
              codex_thread_id TEXT,
              active INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS conversation_messages (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              conversation_id INTEGER NOT NULL,
              role TEXT NOT NULL,
              text TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS pending_codex_messages (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              document_name TEXT NOT NULL,
              powan_id TEXT NOT NULL,
              conversation_id INTEGER NOT NULL,
              message_id INTEGER NOT NULL,
              source TEXT NOT NULL DEFAULT '',
              sender_id TEXT,
              sender_label TEXT NOT NULL DEFAULT '',
              payload_json TEXT NOT NULL DEFAULT '{}',
              status TEXT NOT NULL DEFAULT 'pending',
              error_text TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              claimed_at TEXT,
              processed_at TEXT,
              updated_at TEXT NOT NULL,
              FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
              FOREIGN KEY (message_id) REFERENCES conversation_messages(id) ON DELETE CASCADE
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_pending_codex_messages_message
            ON pending_codex_messages(document_name, message_id);

            CREATE INDEX IF NOT EXISTS idx_pending_codex_messages_target
            ON pending_codex_messages(document_name, powan_id, status, id);

            CREATE TABLE IF NOT EXISTS agent_runs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              conversation_id INTEGER,
              powan_id TEXT,
              status TEXT NOT NULL,
              prompt_json TEXT,
              output_text TEXT,
              error_text TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS api_action_logs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              document_name TEXT NOT NULL,
              powan_id TEXT,
              action TEXT NOT NULL,
              status TEXT NOT NULL,
              request_json TEXT NOT NULL DEFAULT '{}',
              response_json TEXT NOT NULL DEFAULT '{}',
              error_text TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bulk_command_sessions (
              id TEXT NOT NULL,
              document_name TEXT NOT NULL,
              target_json TEXT NOT NULL DEFAULT '[]',
              message_json TEXT NOT NULL DEFAULT '[]',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              PRIMARY KEY (document_name, id)
            );

            CREATE TABLE IF NOT EXISTS child_command_sessions (
              id TEXT NOT NULL,
              document_name TEXT NOT NULL,
              parent_id TEXT NOT NULL,
              status TEXT NOT NULL,
              instruction TEXT NOT NULL DEFAULT '',
              request_json TEXT NOT NULL DEFAULT '{}',
              child_count INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              completed_at TEXT,
              PRIMARY KEY (document_name, id)
            );

            CREATE TABLE IF NOT EXISTS child_command_dispatches (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id TEXT NOT NULL,
              document_name TEXT NOT NULL,
              parent_id TEXT NOT NULL,
              child_id TEXT NOT NULL,
              child_title TEXT NOT NULL DEFAULT '',
              status TEXT NOT NULL,
              instruction TEXT NOT NULL DEFAULT '',
              rendered_text TEXT NOT NULL DEFAULT '',
              conversation_id INTEGER,
              user_message_id INTEGER,
              assistant_message_id INTEGER,
              agent_run_id INTEGER,
              error_text TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              sent_at TEXT,
              started_at TEXT,
              replied_at TEXT,
              updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_child_command_dispatches_session
            ON child_command_dispatches(document_name, session_id);

            CREATE INDEX IF NOT EXISTS idx_child_command_dispatches_child
            ON child_command_dispatches(document_name, child_id, id);

            CREATE TABLE IF NOT EXISTS child_command_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id TEXT NOT NULL,
              dispatch_id INTEGER,
              document_name TEXT NOT NULL,
              parent_id TEXT,
              child_id TEXT,
              event_type TEXT NOT NULL,
              payload_json TEXT NOT NULL DEFAULT '{}',
              created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_child_command_events_session
            ON child_command_events(document_name, session_id, id);

            CREATE INDEX IF NOT EXISTS idx_child_command_events_dispatch
            ON child_command_events(dispatch_id, id);
            """
        )
        connection.execute(
            "INSERT OR REPLACE INTO schema_meta(key, value) VALUES (?, ?)",
            ("schema_version", "1"),
        )
        self.ensure_column(connection, "conversations", "codex_thread_id", "TEXT")
        self.ensure_column(connection, "agent_runs", "pid", "INTEGER")
        connection.commit()

    def ensure_column(self, connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        columns = {
            str(row["name"])
            for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in columns:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def ensure_project(self, project: str) -> Path:
        root = self.project_root(project)
        root.mkdir(parents=True, exist_ok=True)
        created_scaffold = ensure_project_scaffold(root)
        with self.session(project):
            pass
        default_path = self.powan_path(project, self.default_file)
        if default_path.exists():
            self.import_powan_if_needed(project, self.default_file)
        elif not self.document_exists(project, self.default_file):
            self.save_document(project, self.default_file, self.blank_document(), write_export=True)
        if created_scaffold:
            self.log_event(
                "info",
                "powan-project-scaffold-created",
                {
                    "project": self.safe_project_name(project),
                    "files": [str(path.relative_to(root)) for path in created_scaffold],
                },
            )
        return root

    def document_exists(self, project: str, name: str | None = None) -> bool:
        document_name = self.safe_powan_name(name)
        with self.session(project) as connection:
            row = connection.execute(
                "SELECT 1 FROM documents WHERE name = ?",
                (document_name,),
            ).fetchone()
            return row is not None

    def import_powan_if_needed(self, project: str, name: str | None = None) -> None:
        document_name = self.safe_powan_name(name)
        if self.document_exists(project, document_name):
            return
        path = self.powan_path(project, document_name)
        if not path.exists():
            return
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid powan JSON: {exc}") from exc
        self.save_document(project, document_name, document, write_export=False)
        self.log_event("info", "powan-db-import-document", {"project": self.safe_project_name(project), "file": document_name})

    def list_documents(self, project: str) -> list[str]:
        self.ensure_project(project)
        with self.session(project) as connection:
            db_files = [
                str(row["name"])
                for row in connection.execute("SELECT name FROM documents ORDER BY name").fetchall()
            ]
        file_names = sorted(path.name for path in self.project_root(project).glob("*.powan"))
        return sorted(set(db_files + file_names))

    def load_document(self, project: str, name: str | None = None) -> dict[str, Any]:
        document_name = self.safe_powan_name(name)
        self.ensure_project(project)
        self.import_powan_if_needed(project, document_name)
        with self.session(project) as connection:
            row = connection.execute(
                "SELECT document_json FROM documents WHERE name = ?",
                (document_name,),
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Powan file not found")
        try:
            document = json.loads(str(row["document_json"]))
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid ABC JSON in DB: {exc}") from exc
        document.setdefault("version", 1)
        document.setdefault("canvas", {})
        document.setdefault("nodes", [])
        return document

    def save_document(self, project: str, name: str | None, document: dict[str, Any], *, write_export: bool = True) -> None:
        document_name = self.safe_powan_name(name)
        document.setdefault("version", 1)
        document.setdefault("canvas", {})
        document.setdefault("nodes", [])
        now = datetime.now().isoformat(timespec="milliseconds")
        with self.session(project) as connection:
            self._preserve_server_node_state(connection, document_name, document)
            document_json = json.dumps(document, ensure_ascii=False, separators=(",", ":"))
            connection.execute(
                """
                INSERT INTO documents(name, document_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                  document_json = excluded.document_json,
                  updated_at = excluded.updated_at
                """,
                (document_name, document_json, now),
            )
            connection.execute("DELETE FROM powans WHERE document_name = ?", (document_name,))
            connection.execute("DELETE FROM powan_edges WHERE document_name = ?", (document_name,))
            for index, node in enumerate(document.get("nodes") or []):
                self.write_powan_row(connection, document_name, node, now)
                parent_id = node.get("parent")
                if parent_id:
                    connection.execute(
                        """
                        INSERT OR REPLACE INTO powan_edges(document_name, parent_id, child_id, sort_order)
                        VALUES (?, ?, ?, ?)
                        """,
                        (document_name, str(parent_id), str(node.get("id")), index),
                    )
            for key, value in (document.get("canvas") or {}).items():
                connection.execute(
                    """
                    INSERT INTO project_settings(key, value_json, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                      value_json = excluded.value_json,
                      updated_at = excluded.updated_at
                    """,
                    (f"{document_name}:canvas:{key}", json.dumps(value, ensure_ascii=False, separators=(",", ":")), now),
                )
        if write_export:
            self.powan_path(project, document_name).write_text(
                json.dumps(document, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        self.log_event(
            "info",
            "powan-db-save-document",
            {
                "message": f"document saved to DB: {document_name}, {len(document.get('nodes') or [])} nodes",
                "project": self.safe_project_name(project),
                "file": document_name,
                "nodeCount": len(document.get("nodes") or []),
                "console": True,
            },
        )

    def write_powan_row(self, connection: sqlite3.Connection, document_name: str, node: dict[str, Any], now: str) -> None:
        node_id = str(node.get("id") or "")
        if not node_id:
            return
        connection.execute(
            """
            INSERT INTO powans(
              document_name, id, title, body, code, code_language, parent_id,
              style_json, layout_json, nested_layout_json, raw_json, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_name,
                node_id,
                str(node.get("title") or ""),
                str(node.get("body") or ""),
                str(node.get("code") or ""),
                node.get("codeLanguage"),
                node.get("parent"),
                json.dumps(node.get("style") or {}, ensure_ascii=False, separators=(",", ":")),
                json.dumps(node.get("layout") or {}, ensure_ascii=False, separators=(",", ":")),
                json.dumps(node.get("nestedLayoutByParent") or {}, ensure_ascii=False, separators=(",", ":")),
                json.dumps(node, ensure_ascii=False, separators=(",", ":")),
                now,
            ),
        )

    def active_conversation_id(self, project: str, document_name: str, powan_id: str) -> int:
        self.ensure_project(project)
        document_name = self.safe_powan_name(document_name)
        now = datetime.now().isoformat(timespec="milliseconds")
        with self.session(project) as connection:
            row = connection.execute(
                """
                SELECT id FROM conversations
                WHERE document_name = ? AND powan_id = ? AND active = 1
                ORDER BY id DESC LIMIT 1
                """,
                (document_name, powan_id),
            ).fetchone()
            if row:
                return int(row["id"])
            cursor = connection.execute(
                """
                INSERT INTO conversations(document_name, powan_id, title, active, created_at, updated_at)
                VALUES (?, ?, '', 1, ?, ?)
                """,
                (document_name, powan_id, now, now),
            )
            conversation_id = int(cursor.lastrowid)
        self.log_event("info", "powan-db-create-conversation", {"project": self.safe_project_name(project), "file": document_name, "nodeId": powan_id, "conversationId": conversation_id})
        return conversation_id

    def active_conversation(self, project: str, document_name: str, powan_id: str) -> dict[str, Any]:
        conversation_id = self.active_conversation_id(project, document_name, powan_id)
        document_name = self.safe_powan_name(document_name)
        with self.session(project) as connection:
            row = connection.execute(
                """
                SELECT id, document_name, powan_id, title, codex_thread_id, active, created_at, updated_at
                FROM conversations
                WHERE id = ?
                """,
                (conversation_id,),
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {
            "id": int(row["id"]),
            "documentName": row["document_name"],
            "powanId": row["powan_id"],
            "title": row["title"],
            "codexThreadId": row["codex_thread_id"],
            "active": int(row["active"]),
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def list_conversation_sessions(self, project: str, document_name: str, powan_id: str) -> dict[str, Any]:
        self.active_conversation_id(project, document_name, powan_id)
        document_name = self.safe_powan_name(document_name)
        with self.session(project) as connection:
            rows = connection.execute(
                """
                SELECT
                  c.id,
                  c.document_name,
                  c.powan_id,
                  c.title,
                  c.codex_thread_id,
                  c.active,
                  c.created_at,
                  c.updated_at,
                  COUNT(m.id) AS message_count
                FROM conversations c
                LEFT JOIN conversation_messages m ON m.conversation_id = c.id
                WHERE c.document_name = ? AND c.powan_id = ?
                GROUP BY c.id
                ORDER BY c.active DESC, c.updated_at DESC, c.id DESC
                """,
                (document_name, powan_id),
            ).fetchall()
        sessions = [
            {
                "id": int(row["id"]),
                "documentName": row["document_name"],
                "powanId": row["powan_id"],
                "title": row["title"],
                "codexThreadId": row["codex_thread_id"],
                "active": int(row["active"]),
                "createdAt": row["created_at"],
                "updatedAt": row["updated_at"],
                "messageCount": int(row["message_count"]),
            }
            for row in rows
        ]
        active = next((session for session in sessions if session["active"]), None)
        return {
            "activeConversationId": active["id"] if active else None,
            "sessions": sessions,
        }

    def list_document_conversation_sessions(self, project: str, document_name: str) -> dict[str, Any]:
        document_name = self.safe_powan_name(document_name)
        self.ensure_project(project)
        with self.session(project) as connection:
            rows = connection.execute(
                """
                SELECT
                  c.id,
                  c.document_name,
                  c.powan_id,
                  c.title,
                  c.codex_thread_id,
                  c.active,
                  c.created_at,
                  c.updated_at,
                  COUNT(m.id) AS message_count,
                  (
                    SELECT text FROM conversation_messages first_user
                    WHERE first_user.conversation_id = c.id AND first_user.role = 'user'
                    ORDER BY first_user.id ASC
                    LIMIT 1
                  ) AS first_user_text,
                  (
                    SELECT text FROM conversation_messages last_message
                    WHERE last_message.conversation_id = c.id
                    ORDER BY last_message.id DESC
                    LIMIT 1
                  ) AS last_message_text
                FROM conversations c
                LEFT JOIN conversation_messages m ON m.conversation_id = c.id
                WHERE c.document_name = ?
                GROUP BY c.id
                HAVING message_count > 0
                ORDER BY c.updated_at DESC, c.id DESC
                """,
                (document_name,),
            ).fetchall()
        return {
            "sessions": [
                {
                    "id": int(row["id"]),
                    "documentName": row["document_name"],
                    "powanId": row["powan_id"],
                    "title": row["title"],
                    "codexThreadId": row["codex_thread_id"],
                    "active": int(row["active"]),
                    "createdAt": row["created_at"],
                    "updatedAt": row["updated_at"],
                    "messageCount": int(row["message_count"]),
                    "firstUserText": row["first_user_text"] or "",
                    "lastMessageText": row["last_message_text"] or "",
                }
                for row in rows
            ],
        }

    def upsert_bulk_command_session(
        self,
        project: str,
        document_name: str,
        session_id: str,
        target_ids: list[Any],
        target_names: list[Any],
        messages: list[Any],
        created_at: str = "",
        updated_at: str = "",
    ) -> dict[str, Any]:
        document_name = self.safe_powan_name(document_name)
        clean_id = session_id.strip()
        if not clean_id:
            raise HTTPException(status_code=400, detail="Bulk session id is required")
        now = datetime.now().isoformat(timespec="milliseconds")
        clean_targets = {
            "targetIds": [str(value) for value in target_ids[:200]],
            "targetNames": [str(value) for value in target_names[:200]],
        }
        clean_messages = []
        for message in messages[:400]:
            if not isinstance(message, dict):
                continue
            role = str(message.get("role") or "system")
            text = str(message.get("text") or "")
            if role not in {"user", "assistant", "system", "ai"}:
                role = "system"
            clean_messages.append(
                {
                    "role": "assistant" if role == "ai" else role,
                    "text": text,
                    "createdAt": str(message.get("createdAt") or updated_at or created_at or now),
                }
            )
        with self.session(project) as connection:
            existing = connection.execute(
                """
                SELECT created_at FROM bulk_command_sessions
                WHERE document_name = ? AND id = ?
                """,
                (document_name, clean_id),
            ).fetchone()
            final_created_at = str(existing["created_at"]) if existing else (created_at or now)
            final_updated_at = updated_at or now
            connection.execute(
                """
                INSERT INTO bulk_command_sessions(
                  id, document_name, target_json, message_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_name, id) DO UPDATE SET
                  target_json = excluded.target_json,
                  message_json = excluded.message_json,
                  updated_at = excluded.updated_at
                """,
                (
                    clean_id,
                    document_name,
                    json.dumps(clean_targets, ensure_ascii=False, separators=(",", ":")),
                    json.dumps(clean_messages, ensure_ascii=False, separators=(",", ":")),
                    final_created_at,
                    final_updated_at,
                ),
            )
        return {
            "id": clean_id,
            "documentName": document_name,
            "targetIds": clean_targets["targetIds"],
            "targetNames": clean_targets["targetNames"],
            "messages": clean_messages,
            "createdAt": final_created_at,
            "updatedAt": final_updated_at,
        }

    def list_bulk_command_sessions(self, project: str, document_name: str) -> dict[str, Any]:
        document_name = self.safe_powan_name(document_name)
        self.ensure_project(project)
        with self.session(project) as connection:
            rows = connection.execute(
                """
                SELECT id, document_name, target_json, message_json, created_at, updated_at
                FROM bulk_command_sessions
                WHERE document_name = ?
                ORDER BY updated_at DESC, created_at DESC
                """,
                (document_name,),
            ).fetchall()
            action_rows = connection.execute(
                """
                SELECT id, document_name, powan_id, status, request_json, response_json, error_text, created_at
                FROM api_action_logs
                WHERE document_name = ? AND action = 'command-children'
                ORDER BY id DESC
                LIMIT 300
                """,
                (document_name,),
            ).fetchall()
        sessions = []
        session_ids: set[str] = set()
        for row in rows:
            try:
                targets = json.loads(str(row["target_json"] or "{}"))
            except json.JSONDecodeError:
                targets = {}
            try:
                messages = json.loads(str(row["message_json"] or "[]"))
            except json.JSONDecodeError:
                messages = []
            sessions.append(
                {
                    "id": row["id"],
                    "documentName": row["document_name"],
                    "targetIds": targets.get("targetIds") if isinstance(targets, dict) else [],
                    "targetNames": targets.get("targetNames") if isinstance(targets, dict) else [],
                    "messages": messages if isinstance(messages, list) else [],
                    "createdAt": row["created_at"],
                    "updatedAt": row["updated_at"],
                }
            )
            session_ids.add(str(row["id"]))
        for row in action_rows:
            legacy_id = f"legacy-action-{int(row['id'])}"
            if legacy_id in session_ids:
                continue
            try:
                request_payload = json.loads(str(row["request_json"] or "{}"))
            except json.JSONDecodeError:
                request_payload = {}
            try:
                response_payload = json.loads(str(row["response_json"] or "{}"))
            except json.JSONDecodeError:
                response_payload = {}
            linked_session_id = str(request_payload.get("bulkHistoryId") or "") if isinstance(request_payload, dict) else ""
            if linked_session_id and linked_session_id in session_ids:
                continue
            instructions = request_payload.get("instructions") if isinstance(request_payload, dict) else []
            results = response_payload.get("results") if isinstance(response_payload, dict) else []
            target_ids: list[str] = []
            target_names: list[str] = []
            if isinstance(results, list) and results:
                for result in results[:200]:
                    if not isinstance(result, dict):
                        continue
                    node_id = str(result.get("nodeId") or "")
                    if node_id:
                        target_ids.append(node_id)
                    target_names.append(str(result.get("meaning") or node_id or "名前のないポワン"))
            elif isinstance(instructions, list):
                for item in instructions[:200]:
                    if not isinstance(item, dict):
                        continue
                    node_id = str(item.get("childId") or "")
                    if node_id:
                        target_ids.append(node_id)
                    target_names.append(str(item.get("title") or item.get("body") or node_id or "名前のないポワン"))
            common_instruction = str(request_payload.get("instruction") or "") if isinstance(request_payload, dict) else ""
            first_instruction = ""
            if isinstance(instructions, list):
                first_instruction = next(
                    (
                        str(item.get("instruction") or "")
                        for item in instructions
                        if isinstance(item, dict) and str(item.get("instruction") or "").strip()
                    ),
                    "",
                )
            sent_text = common_instruction.strip() or first_instruction.strip() or "一括送信"
            result_lines: list[str] = []
            if isinstance(results, list):
                for result in results[:80]:
                    if not isinstance(result, dict):
                        continue
                    name = str(result.get("meaning") or result.get("nodeId") or "名前のないポワン")
                    status = str(result.get("status") or row["status"] or "")
                    assistant = result.get("assistantMessage") if isinstance(result.get("assistantMessage"), dict) else {}
                    reply = " ".join(str(assistant.get("text") or result.get("error") or "").split())
                    preview = reply[:80]
                    result_lines.append(f"{name}: {status}" + (f" / {preview}" if preview else ""))
            messages = [
                {"role": "user", "text": sent_text, "createdAt": row["created_at"]},
            ]
            result_text = "\n".join(result_lines).strip()
            if result_text:
                messages.append(
                    {
                        "role": "system",
                        "text": f"送信完了: {len(result_lines)}件\n{result_text}",
                        "createdAt": row["created_at"],
                    }
                )
            elif row["error_text"]:
                messages.append(
                    {
                        "role": "system",
                        "text": f"一括送信エラー: {row['error_text']}",
                        "createdAt": row["created_at"],
                    }
                )
            sessions.append(
                {
                    "id": legacy_id,
                    "documentName": row["document_name"],
                    "targetIds": target_ids,
                    "targetNames": target_names,
                    "messages": messages,
                    "createdAt": row["created_at"],
                    "updatedAt": row["created_at"],
                }
            )
        sessions.sort(key=lambda item: str(item.get("updatedAt") or item.get("createdAt") or ""), reverse=True)
        return {"sessions": sessions}

    def start_new_conversation(
        self,
        project: str,
        document_name: str,
        powan_id: str,
        title: str = "",
        summary_text: str = "",
    ) -> dict[str, Any]:
        self.ensure_project(project)
        document_name = self.safe_powan_name(document_name)
        now = datetime.now().isoformat(timespec="milliseconds")
        clean_title = title.strip()
        clean_summary = summary_text.strip()
        with self.session(project) as connection:
            connection.execute(
                """
                UPDATE conversations
                SET active = 0, updated_at = ?
                WHERE document_name = ? AND powan_id = ? AND active = 1
                """,
                (now, document_name, powan_id),
            )
            cursor = connection.execute(
                """
                INSERT INTO conversations(document_name, powan_id, title, active, created_at, updated_at)
                VALUES (?, ?, ?, 1, ?, ?)
                """,
                (document_name, powan_id, clean_title, now, now),
            )
            conversation_id = int(cursor.lastrowid)
            if clean_summary:
                connection.execute(
                    """
                    INSERT INTO conversation_messages(conversation_id, role, text, created_at)
                    VALUES (?, 'system', ?, ?)
                    """,
                    (conversation_id, f"これまでの会話の要約:\n{clean_summary}", now),
                )
        self.log_event(
            "info",
            "powan-db-start-new-conversation",
            {
                "project": self.safe_project_name(project),
                "file": document_name,
                "nodeId": powan_id,
                "conversationId": conversation_id,
                "hasSummary": bool(clean_summary),
            },
        )
        return self.active_conversation(project, document_name, powan_id)

    def set_conversation_codex_thread_id(self, project: str, conversation_id: int, thread_id: str) -> None:
        now = datetime.now().isoformat(timespec="milliseconds")
        with self.session(project) as connection:
            connection.execute(
                "UPDATE conversations SET codex_thread_id = ?, updated_at = ? WHERE id = ?",
                (thread_id, now, conversation_id),
            )
        self.log_event(
            "info",
            "powan-db-set-codex-thread",
            {"project": self.safe_project_name(project), "conversationId": conversation_id, "threadId": thread_id},
        )

    def list_conversation_messages(self, project: str, document_name: str, powan_id: str) -> dict[str, Any]:
        conversation_id = self.active_conversation_id(project, document_name, powan_id)
        return self.conversation_messages_by_id(project, document_name, powan_id, conversation_id)

    def conversation_messages_by_id(
        self,
        project: str,
        document_name: str,
        powan_id: str,
        conversation_id: int,
    ) -> dict[str, Any]:
        document_name = self.safe_powan_name(document_name)
        with self.session(project) as connection:
            conversation = connection.execute(
                """
                SELECT id, document_name, powan_id, title, codex_thread_id, active, created_at, updated_at
                FROM conversations
                WHERE id = ? AND document_name = ? AND powan_id = ?
                """,
                (conversation_id, document_name, powan_id),
            ).fetchone()
            if conversation is None:
                raise HTTPException(status_code=404, detail="Conversation not found")
            rows = connection.execute(
                """
                SELECT id, role, text, created_at FROM conversation_messages
                WHERE conversation_id = ?
                ORDER BY id
                """,
                (conversation_id,),
            ).fetchall()
        return {
            "conversationId": conversation_id,
            "conversation": {
                "id": int(conversation["id"]),
                "documentName": conversation["document_name"],
                "powanId": conversation["powan_id"],
                "title": conversation["title"],
                "codexThreadId": conversation["codex_thread_id"],
                "active": int(conversation["active"]),
                "createdAt": conversation["created_at"],
                "updatedAt": conversation["updated_at"],
            },
            "messages": [
                {"id": int(row["id"]), "role": row["role"], "text": row["text"], "createdAt": row["created_at"]}
                for row in rows
            ],
            "activeRun": self.active_agent_run(project, document_name, powan_id, conversation_id),
        }

    def _agent_run_payload(self, row: sqlite3.Row) -> dict[str, Any]:
        prompt_payload: dict[str, Any] = {}
        try:
            prompt_payload = json.loads(row["prompt_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            prompt_payload = {}
        return {
            "id": int(row["id"]),
            "conversationId": int(row["conversation_id"]) if row["conversation_id"] is not None else None,
            "powanId": row["powan_id"],
            "status": row["status"],
            "pid": int(row["pid"]) if "pid" in row.keys() and row["pid"] is not None else None,
            "threadId": prompt_payload.get("threadId") or "",
            "source": prompt_payload.get("source") or "",
            "userText": prompt_payload.get("userText") or "",
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def active_agent_run(
        self,
        project: str,
        document_name: str,
        powan_id: str,
        conversation_id: int | None = None,
    ) -> dict[str, Any] | None:
        document_name = self.safe_powan_name(document_name)
        parameters: list[Any] = [document_name, powan_id]
        conversation_filter = ""
        if conversation_id is not None:
            conversation_filter = "AND ar.conversation_id = ?"
            parameters.append(int(conversation_id))
        with self.session(project) as connection:
            row = connection.execute(
                f"""
                SELECT ar.id, ar.conversation_id, ar.powan_id, ar.status, ar.pid,
                       ar.prompt_json, ar.created_at, ar.updated_at
                FROM agent_runs ar
                JOIN conversations c ON c.id = ar.conversation_id
                WHERE c.document_name = ?
                  AND ar.powan_id = ?
                  AND ar.status = 'running'
                  {conversation_filter}
                ORDER BY ar.updated_at DESC, ar.id DESC
                LIMIT 1
                """,
                parameters,
            ).fetchone()
        return self._agent_run_payload(row) if row else None

    def list_running_agent_runs(self, project: str, document_name: str) -> list[dict[str, Any]]:
        document_name = self.safe_powan_name(document_name)
        with self.session(project) as connection:
            rows = connection.execute(
                """
                SELECT ar.id, ar.conversation_id, ar.powan_id, ar.status, ar.pid,
                       ar.prompt_json, ar.created_at, ar.updated_at
                FROM agent_runs ar
                JOIN conversations c ON c.id = ar.conversation_id
                WHERE c.document_name = ?
                  AND ar.status = 'running'
                ORDER BY ar.updated_at DESC, ar.id DESC
                """,
                (document_name,),
            ).fetchall()
        return [self._agent_run_payload(row) for row in rows]

    def append_conversation_message(
        self,
        project: str,
        document_name: str,
        powan_id: str,
        role: str,
        text: str,
    ) -> dict[str, Any]:
        conversation_id = self.active_conversation_id(project, document_name, powan_id)
        return self.append_conversation_message_to_conversation(
            project,
            document_name,
            powan_id,
            conversation_id,
            role,
            text,
        )

    def append_conversation_message_to_conversation(
        self,
        project: str,
        document_name: str,
        powan_id: str,
        conversation_id: int,
        role: str,
        text: str,
    ) -> dict[str, Any]:
        document_name = self.safe_powan_name(document_name)
        clean_role = role.strip().lower()
        if clean_role not in {"user", "assistant", "system"}:
            raise HTTPException(status_code=400, detail="Invalid message role")
        clean_text = text.strip()
        if not clean_text:
            raise HTTPException(status_code=400, detail="Message text is required")
        now = datetime.now().isoformat(timespec="milliseconds")
        document_to_export: dict[str, Any] | None = None
        with self.session(project) as connection:
            row = connection.execute(
                """
                SELECT id FROM conversations
                WHERE id = ? AND document_name = ? AND powan_id = ?
                """,
                (int(conversation_id), document_name, powan_id),
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Conversation not found")
            cursor = connection.execute(
                """
                INSERT INTO conversation_messages(conversation_id, role, text, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (int(conversation_id), clean_role, clean_text, now),
            )
            connection.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, int(conversation_id)),
            )
            if clean_role == "assistant":
                document_to_export = self._set_powan_codex_state(connection, document_name, powan_id, None, now)
            message_id = int(cursor.lastrowid)
        if document_to_export is not None:
            self._write_document_export(project, document_name, document_to_export)
        self.log_event(
            "info",
            "powan-db-append-conversation-message",
            {
                "project": self.safe_project_name(project),
                "file": self.safe_powan_name(document_name),
                "nodeId": powan_id,
                "conversationId": int(conversation_id),
                "messageId": message_id,
                "role": clean_role,
                "length": len(clean_text),
            },
        )
        return {
            "id": message_id,
            "conversationId": int(conversation_id),
            "role": clean_role,
            "text": clean_text,
            "createdAt": now,
        }

    def queue_pending_codex_message(
        self,
        project: str,
        document_name: str,
        powan_id: str,
        conversation_id: int,
        message_id: int,
        *,
        source: str = "",
        sender_id: str | None = None,
        sender_label: str = "",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        document_name = self.safe_powan_name(document_name)
        now = datetime.now().isoformat(timespec="milliseconds")
        payload_json = json.dumps(payload or {}, ensure_ascii=False, separators=(",", ":"))
        with self.session(project) as connection:
            row = connection.execute(
                """
                SELECT id FROM pending_codex_messages
                WHERE document_name = ? AND message_id = ?
                """,
                (document_name, int(message_id)),
            ).fetchone()
            if row is not None:
                pending_id = int(row["id"])
            else:
                cursor = connection.execute(
                    """
                    INSERT INTO pending_codex_messages(
                      document_name, powan_id, conversation_id, message_id,
                      source, sender_id, sender_label, payload_json,
                      status, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                    """,
                    (
                        document_name,
                        powan_id,
                        int(conversation_id),
                        int(message_id),
                        source,
                        sender_id,
                        sender_label,
                        payload_json,
                        now,
                        now,
                    ),
                )
                pending_id = int(cursor.lastrowid)
        self.log_event(
            "info",
            "powan-db-pending-codex-message-queued",
            {
                "project": self.safe_project_name(project),
                "file": document_name,
                "nodeId": powan_id,
                "conversationId": int(conversation_id),
                "messageId": int(message_id),
                "pendingId": pending_id,
                "source": source,
            },
        )
        return {
            "id": pending_id,
            "documentName": document_name,
            "powanId": powan_id,
            "conversationId": int(conversation_id),
            "messageId": int(message_id),
            "source": source,
            "status": "pending",
            "createdAt": now,
        }

    def claim_pending_codex_messages(
        self,
        project: str,
        document_name: str,
        powan_id: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        document_name = self.safe_powan_name(document_name)
        now = datetime.now().isoformat(timespec="milliseconds")
        with self.session(project) as connection:
            rows = connection.execute(
                """
                SELECT
                  p.id, p.document_name, p.powan_id, p.conversation_id,
                  p.message_id, p.source, p.sender_id, p.sender_label,
                  p.payload_json, p.created_at,
                  m.role, m.text, m.created_at AS message_created_at
                FROM pending_codex_messages p
                JOIN conversation_messages m ON m.id = p.message_id
                WHERE p.document_name = ?
                  AND p.powan_id = ?
                  AND p.status IN ('pending', 'claimed')
                ORDER BY p.id
                LIMIT ?
                """,
                (document_name, powan_id, int(limit)),
            ).fetchall()
            ids = [int(row["id"]) for row in rows]
            if ids:
                placeholders = ",".join("?" for _ in ids)
                connection.execute(
                    f"""
                    UPDATE pending_codex_messages
                    SET status = 'claimed',
                        claimed_at = COALESCE(claimed_at, ?),
                        updated_at = ?
                    WHERE id IN ({placeholders})
                    """,
                    (now, now, *ids),
                )
        claimed: list[dict[str, Any]] = []
        for row in rows:
            payload: dict[str, Any] = {}
            try:
                payload = json.loads(row["payload_json"] or "{}")
            except (TypeError, json.JSONDecodeError):
                payload = {}
            claimed.append(
                {
                    "id": int(row["id"]),
                    "documentName": row["document_name"],
                    "powanId": row["powan_id"],
                    "conversationId": int(row["conversation_id"]),
                    "messageId": int(row["message_id"]),
                    "source": row["source"],
                    "senderId": row["sender_id"],
                    "senderLabel": row["sender_label"],
                    "payload": payload,
                    "role": row["role"],
                    "text": row["text"],
                    "createdAt": row["created_at"],
                    "messageCreatedAt": row["message_created_at"],
                }
            )
        if claimed:
            self.log_event(
                "info",
                "powan-db-pending-codex-messages-claimed",
                {
                    "project": self.safe_project_name(project),
                    "file": document_name,
                    "nodeId": powan_id,
                    "count": len(claimed),
                    "ids": [item["id"] for item in claimed],
                },
            )
        return claimed

    def list_pending_codex_message_targets(
        self,
        project: str | None = None,
        document_name: str | None = None,
    ) -> list[dict[str, Any]]:
        projects = [self.safe_project_name(project)] if project else [
            path.name
            for path in self.work_root.iterdir()
            if path.is_dir() and (path / "powan.db").is_file()
        ]
        targets: list[dict[str, Any]] = []
        document_filter = ""
        parameters: list[Any] = []
        if document_name is not None:
            document_filter = "AND document_name = ?"
            parameters.append(self.safe_powan_name(document_name))
        for project_name in projects:
            try:
                with self.session(project_name) as connection:
                    rows = connection.execute(
                        f"""
                        SELECT document_name, powan_id, COUNT(*) AS count
                        FROM pending_codex_messages
                        WHERE status IN ('pending', 'claimed')
                          {document_filter}
                        GROUP BY document_name, powan_id
                        ORDER BY document_name, powan_id
                        """,
                        parameters,
                    ).fetchall()
            except sqlite3.DatabaseError as exc:
                self.log_event(
                    "error",
                    "powan-db-list-pending-codex-targets-project-failed",
                    {
                        "project": project_name,
                        "error": repr(exc),
                    },
                )
                continue
            for row in rows:
                targets.append(
                    {
                        "project": project_name,
                        "documentName": row["document_name"],
                        "powanId": row["powan_id"],
                        "count": int(row["count"]),
                    }
                )
        return targets

    def finish_pending_codex_messages(
        self,
        project: str,
        pending_ids: list[int],
        status: str,
        *,
        error_text: str = "",
    ) -> None:
        ids = [int(item) for item in pending_ids if item is not None]
        if not ids:
            return
        clean_status = status if status in {"processed", "pending", "failed"} else "processed"
        now = datetime.now().isoformat(timespec="milliseconds")
        with self.session(project) as connection:
            placeholders = ",".join("?" for _ in ids)
            if clean_status == "pending":
                connection.execute(
                    f"""
                    UPDATE pending_codex_messages
                    SET status = 'pending',
                        error_text = ?,
                        claimed_at = NULL,
                        updated_at = ?
                    WHERE id IN ({placeholders})
                    """,
                    (error_text, now, *ids),
                )
            else:
                connection.execute(
                    f"""
                    UPDATE pending_codex_messages
                    SET status = ?,
                        error_text = ?,
                        processed_at = ?,
                        updated_at = ?
                    WHERE id IN ({placeholders})
                    """,
                    (clean_status, error_text, now, now, *ids),
                )
        self.log_event(
            "info" if clean_status != "failed" else "error",
            "powan-db-pending-codex-messages-finished",
            {
                "project": self.safe_project_name(project),
                "ids": ids,
                "status": clean_status,
                "error": error_text[:240] if error_text else "",
            },
        )

    def record_agent_run(
        self,
        project: str,
        conversation_id: int,
        powan_id: str,
        status: str,
        prompt_payload: dict[str, Any],
        output_text: str = "",
        error_text: str = "",
    ) -> dict[str, Any]:
        now = datetime.now().isoformat(timespec="milliseconds")
        with self.session(project) as connection:
            cursor = connection.execute(
                """
                INSERT INTO agent_runs(
                  conversation_id, powan_id, status, prompt_json, output_text,
                  error_text, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    powan_id,
                    status,
                    json.dumps(prompt_payload, ensure_ascii=False, separators=(",", ":")),
                    output_text,
                    error_text,
                    now,
                    now,
                ),
            )
            run_id = int(cursor.lastrowid)
        self.log_event(
            "info" if status == "completed" else "error",
            "powan-db-record-agent-run",
            {
                "project": self.safe_project_name(project),
                "conversationId": conversation_id,
                "runId": run_id,
                "nodeId": powan_id,
                "status": status,
                "outputLength": len(output_text),
                "errorLength": len(error_text),
            },
        )
        return {
            "id": run_id,
            "conversationId": conversation_id,
            "powanId": powan_id,
            "status": status,
            "createdAt": now,
        }

    def start_agent_run(
        self,
        project: str,
        conversation_id: int,
        powan_id: str,
        prompt_payload: dict[str, Any],
    ) -> dict[str, Any]:
        now = datetime.now().isoformat(timespec="milliseconds")
        with self.session(project) as connection:
            cursor = connection.execute(
                """
                INSERT INTO agent_runs(
                  conversation_id, powan_id, status, prompt_json, output_text,
                  error_text, created_at, updated_at
                )
                VALUES (?, ?, 'running', ?, '', '', ?, ?)
                """,
                (
                    conversation_id,
                    powan_id,
                    json.dumps(prompt_payload, ensure_ascii=False, separators=(",", ":")),
                    now,
                    now,
                ),
            )
            run_id = int(cursor.lastrowid)
        self.log_event(
            "info",
            "powan-db-start-agent-run",
            {
                "project": self.safe_project_name(project),
                "conversationId": conversation_id,
                "runId": run_id,
                "nodeId": powan_id,
                "status": "running",
            },
        )
        return {
            "id": run_id,
            "conversationId": conversation_id,
            "powanId": powan_id,
            "status": "running",
            "createdAt": now,
        }

    def set_agent_run_pid(self, project: str, run_id: int, pid: int) -> None:
        now = datetime.now().isoformat(timespec="milliseconds")
        with self.session(project) as connection:
            connection.execute(
                """
                UPDATE agent_runs
                SET pid = ?, updated_at = ?
                WHERE id = ? AND status = 'running'
                """,
                (int(pid), now, int(run_id)),
            )
        self.log_event(
            "info",
            "powan-db-set-agent-run-pid",
            {"project": self.safe_project_name(project), "runId": int(run_id), "pid": int(pid)},
        )

    def fail_agent_run_if_running(self, project: str, run_id: int, error_text: str) -> dict[str, Any] | None:
        now = datetime.now().isoformat(timespec="milliseconds")
        with self.session(project) as connection:
            row = connection.execute(
                """
                SELECT ar.id, ar.conversation_id, ar.powan_id, ar.status, ar.prompt_json,
                       ar.created_at, c.document_name
                FROM agent_runs ar
                LEFT JOIN conversations c ON c.id = ar.conversation_id
                WHERE ar.id = ?
                """,
                (int(run_id),),
            ).fetchone()
            if row is None or row["status"] != "running":
                return None
            try:
                prompt_payload = json.loads(row["prompt_json"] or "{}")
            except (TypeError, json.JSONDecodeError):
                prompt_payload = {}
            prompt_payload["reconciledDead"] = True
            connection.execute(
                """
                UPDATE agent_runs
                SET status = 'failed',
                    prompt_json = ?,
                    error_text = ?,
                    updated_at = ?
                WHERE id = ? AND status = 'running'
                """,
                (
                    json.dumps(prompt_payload, ensure_ascii=False, separators=(",", ":")),
                    error_text,
                    now,
                    int(run_id),
                ),
            )
        payload = {
            "id": int(row["id"]),
            "conversationId": int(row["conversation_id"]) if row["conversation_id"] is not None else None,
            "powanId": row["powan_id"],
            "documentName": row["document_name"] or self.default_file,
            "status": "failed",
            "updatedAt": now,
            "errorText": error_text,
        }
        self.log_event(
            "warn",
            "powan-db-reconcile-dead-agent-run",
            {
                "project": self.safe_project_name(project),
                "runId": payload["id"],
                "nodeId": payload["powanId"],
                "conversationId": payload["conversationId"],
            },
        )
        return payload

    def finish_agent_run(
        self,
        project: str,
        run_id: int,
        status: str,
        prompt_payload: dict[str, Any],
        output_text: str = "",
        error_text: str = "",
    ) -> dict[str, Any]:
        now = datetime.now().isoformat(timespec="milliseconds")
        with self.session(project) as connection:
            row = connection.execute(
                """
                SELECT id, conversation_id, powan_id, created_at
                FROM agent_runs
                WHERE id = ?
                """,
                (int(run_id),),
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Agent run not found")
            connection.execute(
                """
                UPDATE agent_runs
                SET status = ?,
                    prompt_json = ?,
                    output_text = ?,
                    error_text = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    json.dumps(prompt_payload, ensure_ascii=False, separators=(",", ":")),
                    output_text,
                    error_text,
                    now,
                    int(run_id),
                ),
            )
        self.log_event(
            "info" if status == "completed" else "error" if status == "failed" else "info",
            "powan-db-finish-agent-run",
            {
                "project": self.safe_project_name(project),
                "conversationId": int(row["conversation_id"]),
                "runId": int(run_id),
                "nodeId": row["powan_id"],
                "status": status,
                "outputLength": len(output_text),
                "errorLength": len(error_text),
            },
        )
        return {
            "id": int(run_id),
            "conversationId": int(row["conversation_id"]),
            "powanId": row["powan_id"],
            "status": status,
            "createdAt": row["created_at"],
            "updatedAt": now,
        }

    def create_child_command_session(
        self,
        project: str,
        document_name: str,
        session_id: str,
        parent_id: str,
        instruction: str,
        request_payload: dict[str, Any] | list[Any] | None,
        child_count: int,
    ) -> dict[str, Any]:
        document_name = self.safe_powan_name(document_name)
        now = datetime.now().isoformat(timespec="milliseconds")
        request_json = json.dumps(request_payload or {}, ensure_ascii=False, separators=(",", ":"))
        with self.session(project) as connection:
            connection.execute(
                """
                INSERT INTO child_command_sessions(
                  id, document_name, parent_id, status, instruction,
                  request_json, child_count, created_at, updated_at
                )
                VALUES (?, ?, ?, 'received', ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    document_name,
                    parent_id,
                    instruction,
                    request_json,
                    int(child_count),
                    now,
                    now,
                ),
            )
            connection.execute(
                """
                INSERT INTO child_command_events(
                  session_id, dispatch_id, document_name, parent_id, child_id,
                  event_type, payload_json, created_at
                )
                VALUES (?, NULL, ?, ?, NULL, 'received', ?, ?)
                """,
                (
                    session_id,
                    document_name,
                    parent_id,
                    json.dumps({"childCount": int(child_count)}, ensure_ascii=False, separators=(",", ":")),
                    now,
                ),
            )
        self.log_event(
            "info",
            "powan-db-child-command-session-received",
            {
                "project": self.safe_project_name(project),
                "file": document_name,
                "sessionId": session_id,
                "parentId": parent_id,
                "childCount": int(child_count),
            },
        )
        return {
            "id": session_id,
            "documentName": document_name,
            "parentId": parent_id,
            "status": "received",
            "childCount": int(child_count),
            "createdAt": now,
        }

    def update_child_command_session_status(
        self,
        project: str,
        document_name: str,
        session_id: str,
        status: str,
    ) -> None:
        document_name = self.safe_powan_name(document_name)
        now = datetime.now().isoformat(timespec="milliseconds")
        completed_at = now if status in {"completed", "failed", "cancelled"} else None
        with self.session(project) as connection:
            row = connection.execute(
                """
                SELECT parent_id FROM child_command_sessions
                WHERE document_name = ? AND id = ?
                """,
                (document_name, session_id),
            ).fetchone()
            parent_id = str(row["parent_id"]) if row is not None else ""
            if completed_at:
                connection.execute(
                    """
                    UPDATE child_command_sessions
                    SET status = ?, updated_at = ?, completed_at = ?
                    WHERE document_name = ? AND id = ?
                    """,
                    (status, now, completed_at, document_name, session_id),
                )
            else:
                connection.execute(
                    """
                    UPDATE child_command_sessions
                    SET status = ?, updated_at = ?
                    WHERE document_name = ? AND id = ?
                    """,
                    (status, now, document_name, session_id),
                )
            connection.execute(
                """
                INSERT INTO child_command_events(
                  session_id, dispatch_id, document_name, parent_id, child_id,
                  event_type, payload_json, created_at
                )
                VALUES (?, NULL, ?, ?, NULL, ?, ?, ?)
                """,
                (
                    session_id,
                    document_name,
                    parent_id,
                    f"session-{status}",
                    json.dumps({"status": status}, ensure_ascii=False, separators=(",", ":")),
                    now,
                ),
            )
        self.log_event(
            "info" if status == "completed" else "error" if status == "failed" else "info",
            "powan-db-child-command-session-status",
            {
                "project": self.safe_project_name(project),
                "file": document_name,
                "sessionId": session_id,
                "status": status,
            },
        )

    def record_child_command_dispatch(
        self,
        project: str,
        document_name: str,
        session_id: str,
        parent_id: str,
        child_id: str,
        child_title: str,
        instruction: str,
        rendered_text: str,
        conversation_id: int,
        user_message_id: int,
    ) -> dict[str, Any]:
        document_name = self.safe_powan_name(document_name)
        now = datetime.now().isoformat(timespec="milliseconds")
        with self.session(project) as connection:
            cursor = connection.execute(
                """
                INSERT INTO child_command_dispatches(
                  session_id, document_name, parent_id, child_id, child_title,
                  status, instruction, rendered_text, conversation_id,
                  user_message_id, created_at, sent_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, 'sent', ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    document_name,
                    parent_id,
                    child_id,
                    child_title,
                    instruction,
                    rendered_text,
                    int(conversation_id),
                    int(user_message_id),
                    now,
                    now,
                    now,
                ),
            )
            dispatch_id = int(cursor.lastrowid)
            connection.execute(
                """
                INSERT INTO child_command_events(
                  session_id, dispatch_id, document_name, parent_id, child_id,
                  event_type, payload_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, 'sent', ?, ?)
                """,
                (
                    session_id,
                    dispatch_id,
                    document_name,
                    parent_id,
                    child_id,
                    json.dumps(
                        {
                            "conversationId": int(conversation_id),
                            "userMessageId": int(user_message_id),
                        },
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                    now,
                ),
            )
        self.log_event(
            "info",
            "powan-db-child-command-dispatch-sent",
            {
                "project": self.safe_project_name(project),
                "file": document_name,
                "sessionId": session_id,
                "dispatchId": dispatch_id,
                "parentId": parent_id,
                "childId": child_id,
                "conversationId": int(conversation_id),
                "messageId": int(user_message_id),
            },
        )
        return {
            "id": dispatch_id,
            "sessionId": session_id,
            "documentName": document_name,
            "parentId": parent_id,
            "childId": child_id,
            "status": "sent",
            "conversationId": int(conversation_id),
            "userMessageId": int(user_message_id),
            "createdAt": now,
            "sentAt": now,
        }

    def mark_child_command_dispatch_started(self, project: str, dispatch_id: int) -> None:
        now = datetime.now().isoformat(timespec="milliseconds")
        with self.session(project) as connection:
            connection.execute(
                """
                UPDATE child_command_dispatches
                SET status = 'started', started_at = COALESCE(started_at, ?), updated_at = ?
                WHERE id = ?
                """,
                (now, now, int(dispatch_id)),
            )
            row = connection.execute(
                """
                SELECT session_id, document_name, parent_id, child_id
                FROM child_command_dispatches
                WHERE id = ?
                """,
                (int(dispatch_id),),
            ).fetchone()
            if row is not None:
                connection.execute(
                    """
                    INSERT INTO child_command_events(
                      session_id, dispatch_id, document_name, parent_id, child_id,
                      event_type, payload_json, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, 'started', '{}', ?)
                    """,
                    (
                        row["session_id"],
                        int(dispatch_id),
                        row["document_name"],
                        row["parent_id"],
                        row["child_id"],
                        now,
                    ),
                )
        self.log_event(
            "info",
            "powan-db-child-command-dispatch-started",
            {"project": self.safe_project_name(project), "dispatchId": int(dispatch_id)},
        )

    def mark_child_command_dispatch_replied(
        self,
        project: str,
        dispatch_id: int,
        status: str,
        assistant_message_id: int | None = None,
        agent_run_id: int | None = None,
        error_text: str = "",
    ) -> None:
        now = datetime.now().isoformat(timespec="milliseconds")
        clean_status = status if status in {"completed", "failed", "cancelled"} else "completed"
        with self.session(project) as connection:
            connection.execute(
                """
                UPDATE child_command_dispatches
                SET status = ?,
                    assistant_message_id = ?,
                    agent_run_id = ?,
                    error_text = ?,
                    replied_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    clean_status,
                    assistant_message_id,
                    agent_run_id,
                    error_text,
                    now,
                    now,
                    int(dispatch_id),
                ),
            )
            row = connection.execute(
                """
                SELECT session_id, document_name, parent_id, child_id
                FROM child_command_dispatches
                WHERE id = ?
                """,
                (int(dispatch_id),),
            ).fetchone()
            if row is not None:
                connection.execute(
                    """
                    INSERT INTO child_command_events(
                      session_id, dispatch_id, document_name, parent_id, child_id,
                      event_type, payload_json, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, 'replied', ?, ?)
                    """,
                    (
                        row["session_id"],
                        int(dispatch_id),
                        row["document_name"],
                        row["parent_id"],
                        row["child_id"],
                        json.dumps(
                            {
                                "status": clean_status,
                                "assistantMessageId": assistant_message_id,
                                "agentRunId": agent_run_id,
                                "error": error_text,
                            },
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                        now,
                    ),
                )
        self.log_event(
            "info" if clean_status == "completed" else "error",
            "powan-db-child-command-dispatch-replied",
            {
                "project": self.safe_project_name(project),
                "dispatchId": int(dispatch_id),
                "status": clean_status,
                "assistantMessageId": assistant_message_id,
                "agentRunId": agent_run_id,
                "error": error_text[:240] if error_text else "",
            },
        )

    def fail_child_command_dispatches_for_run(
        self,
        project: str,
        document_name: str,
        powan_id: str,
        conversation_id: int | None,
        error_text: str,
    ) -> list[dict[str, Any]]:
        if conversation_id is None:
            return []
        document_name = self.safe_powan_name(document_name)
        now = datetime.now().isoformat(timespec="milliseconds")
        failed: list[dict[str, Any]] = []
        touched_sessions: set[str] = set()
        with self.session(project) as connection:
            rows = connection.execute(
                """
                SELECT id, session_id, document_name, parent_id, child_id
                FROM child_command_dispatches
                WHERE document_name = ?
                  AND child_id = ?
                  AND conversation_id = ?
                  AND status NOT IN ('completed', 'failed', 'cancelled', 'skipped')
                """,
                (document_name, powan_id, int(conversation_id)),
            ).fetchall()
            for row in rows:
                dispatch_id = int(row["id"])
                session_id = str(row["session_id"])
                touched_sessions.add(session_id)
                connection.execute(
                    """
                    UPDATE child_command_dispatches
                    SET status = 'failed',
                        error_text = ?,
                        replied_at = COALESCE(replied_at, ?),
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (error_text, now, now, dispatch_id),
                )
                connection.execute(
                    """
                    INSERT INTO child_command_events(
                      session_id, dispatch_id, document_name, parent_id, child_id,
                      event_type, payload_json, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, 'reconciled-failed', ?, ?)
                    """,
                    (
                        session_id,
                        dispatch_id,
                        row["document_name"],
                        row["parent_id"],
                        row["child_id"],
                        json.dumps({"error": error_text}, ensure_ascii=False, separators=(",", ":")),
                        now,
                    ),
                )
                failed.append(
                    {
                        "id": dispatch_id,
                        "sessionId": session_id,
                        "childId": row["child_id"],
                        "conversationId": int(conversation_id),
                    }
                )
            for session_id in touched_sessions:
                remaining = connection.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM child_command_dispatches
                    WHERE document_name = ?
                      AND session_id = ?
                      AND status NOT IN ('completed', 'failed', 'cancelled', 'skipped')
                    """,
                    (document_name, session_id),
                ).fetchone()
                if int(remaining["count"] if remaining is not None else 0) > 0:
                    continue
                session = connection.execute(
                    """
                    SELECT parent_id, status
                    FROM child_command_sessions
                    WHERE document_name = ? AND id = ?
                    """,
                    (document_name, session_id),
                ).fetchone()
                if session is None or session["status"] in {"completed", "failed", "cancelled"}:
                    continue
                connection.execute(
                    """
                    UPDATE child_command_sessions
                    SET status = 'failed',
                        updated_at = ?,
                        completed_at = COALESCE(completed_at, ?)
                    WHERE document_name = ? AND id = ?
                    """,
                    (now, now, document_name, session_id),
                )
                connection.execute(
                    """
                    INSERT INTO child_command_events(
                      session_id, dispatch_id, document_name, parent_id, child_id,
                      event_type, payload_json, created_at
                    )
                    VALUES (?, NULL, ?, ?, NULL, 'session-reconciled-failed', ?, ?)
                    """,
                    (
                        session_id,
                        document_name,
                        session["parent_id"],
                        json.dumps({"error": error_text}, ensure_ascii=False, separators=(",", ":")),
                        now,
                    ),
                )
        if failed:
            self.log_event(
                "warn",
                "powan-db-reconcile-child-dispatches",
                {
                    "project": self.safe_project_name(project),
                    "file": document_name,
                    "nodeId": powan_id,
                    "conversationId": int(conversation_id),
                    "count": len(failed),
                },
            )
        return failed

    def record_api_action(
        self,
        project: str,
        document_name: str,
        powan_id: str | None,
        action: str,
        status: str,
        request_payload: dict[str, Any] | list[Any] | None = None,
        response_payload: dict[str, Any] | list[Any] | None = None,
        error_text: str = "",
    ) -> dict[str, Any]:
        document_name = self.safe_powan_name(document_name)
        now = datetime.now().isoformat(timespec="milliseconds")
        request_json = json.dumps(request_payload or {}, ensure_ascii=False, separators=(",", ":"))
        response_json = json.dumps(response_payload or {}, ensure_ascii=False, separators=(",", ":"))
        with self.session(project) as connection:
            cursor = connection.execute(
                """
                INSERT INTO api_action_logs(
                  document_name, powan_id, action, status, request_json,
                  response_json, error_text, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_name,
                    powan_id,
                    action,
                    status,
                    request_json,
                    response_json,
                    error_text,
                    now,
                ),
            )
            log_id = int(cursor.lastrowid)
        self.log_event(
            "info" if status == "completed" else "error",
            "powan-db-record-api-action",
            {
                "message": f"api action recorded: {action}/{status} #{log_id}",
                "project": self.safe_project_name(project),
                "file": document_name,
                "nodeId": powan_id,
                "action": action,
                "status": status,
                "logId": log_id,
                "error": error_text[:240] if error_text else "",
            },
        )
        return {
            "id": log_id,
            "documentName": document_name,
            "powanId": powan_id,
            "action": action,
            "status": status,
            "createdAt": now,
        }

    def list_api_action_logs(
        self,
        project: str,
        document_name: str | None = None,
        powan_id: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        document_name = self.safe_powan_name(document_name or self.default_file)
        clean_limit = min(1000, max(1, int(limit)))
        params: list[Any] = [document_name]
        where = ["document_name = ?"]
        if powan_id:
            where.append("powan_id = ?")
            params.append(powan_id)
        params.append(clean_limit)
        with self.session(project) as connection:
            rows = connection.execute(
                f"""
                SELECT id, document_name, powan_id, action, status,
                       request_json, response_json, error_text, created_at
                FROM api_action_logs
                WHERE {" AND ".join(where)}
                ORDER BY id DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        logs: list[dict[str, Any]] = []
        for row in rows:
            try:
                request_payload = json.loads(row["request_json"])
            except json.JSONDecodeError:
                request_payload = {}
            try:
                response_payload = json.loads(row["response_json"])
            except json.JSONDecodeError:
                response_payload = {}
            logs.append(
                {
                    "id": int(row["id"]),
                    "documentName": row["document_name"],
                    "powanId": row["powan_id"],
                    "action": row["action"],
                    "status": row["status"],
                    "request": request_payload,
                    "response": response_payload,
                    "error": row["error_text"],
                    "createdAt": row["created_at"],
                }
            )
        return {
            "project": self.safe_project_name(project),
            "file": document_name,
            "logs": logs,
        }
