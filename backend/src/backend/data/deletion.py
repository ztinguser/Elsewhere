import json
import os
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from zipfile import BadZipFile, ZipFile

from backend.storage.database import connect


def deletion_scope(connection, branch_id=None):
    if branch_id is None:
        branches = [row[0] for row in connection.execute("SELECT id FROM branches")]
        tasks = [row[0] for row in connection.execute("SELECT id FROM tasks")]
    else:
        branches = [row[0] for row in connection.execute(
            """WITH RECURSIVE descendants(id) AS (
                   SELECT id FROM branches WHERE id = ?
                   UNION ALL SELECT b.id FROM branches b JOIN descendants d ON b.parent_id = d.id
               ) SELECT id FROM descendants""", (branch_id,))]
        tasks = [row["id"] for row in connection.execute("SELECT id, branch_id FROM tasks")
                 if row["branch_id"] in branches]
    versions = [row["fact_version_id"] for row in connection.execute("SELECT id, fact_version_id FROM branches")
                if row["id"] in branches]
    return {"all": branch_id is None, "branches": branches, "tasks": tasks, "versions": versions}


def stop_tasks(connection, scope):
    connection.executemany(
        """UPDATE tasks SET status = 'cancelled', updated_at = ?
           WHERE id = ? AND status NOT IN ('completed', 'failed', 'cancelled')""",
        [(datetime.now(UTC).isoformat(), task_id) for task_id in scope["tasks"]],
    )


def delete_life(path, scope):
    with connect(path) as connection:
        # 分支来源、复制前缀和重试任务有相互引用，统一在提交时校验。
        connection.execute("PRAGMA defer_foreign_keys = ON")
        connection.execute("PRAGMA secure_delete = ON")
        connection.execute("CREATE TEMP TABLE removed_branches (id TEXT PRIMARY KEY)")
        connection.executemany("INSERT INTO removed_branches VALUES (?)", [(b,) for b in scope["branches"]])
        connection.execute("CREATE TEMP TABLE removed_tasks (id TEXT PRIMARY KEY)")
        connection.executemany("INSERT INTO removed_tasks VALUES (?)", [(t,) for t in scope["tasks"]])
        connection.execute("DELETE FROM task_events WHERE task_id IN removed_tasks")
        connection.execute("DELETE FROM tasks WHERE id IN removed_tasks")
        connection.execute("DELETE FROM reading_positions WHERE branch_id IN removed_branches")
        connection.execute("""DELETE FROM paragraphs WHERE version_id IN (
            SELECT v.id FROM chapter_versions v JOIN chapters c ON c.id=v.chapter_id
            WHERE c.branch_id IN removed_branches)""")
        connection.execute("DELETE FROM chapter_versions WHERE chapter_id IN (SELECT id FROM chapters WHERE branch_id IN removed_branches)")
        connection.execute("DELETE FROM chapters WHERE branch_id IN removed_branches")
        connection.execute("DELETE FROM events WHERE branch_id IN removed_branches")
        connection.execute("DELETE FROM simulation_choices WHERE stage_id IN (SELECT id FROM simulation_stages WHERE branch_id IN removed_branches)")
        connection.execute("DELETE FROM simulation_stages WHERE branch_id IN removed_branches")
        connection.execute("DELETE FROM fork_plans WHERE branch_id IN removed_branches")
        connection.execute("DELETE FROM fork_requests WHERE branch_id IN removed_branches")
        connection.execute("DELETE FROM branches WHERE id IN removed_branches")
        connection.executemany(
            "DELETE FROM fact_versions WHERE id = ? AND id NOT IN (SELECT fact_version_id FROM branches)",
            [(version,) for version in scope["versions"]],
        )
        if scope["all"]:
            for table in ("fork_requests", "fact_versions", "fact_sources", "fact_nodes", "fragments", "drafts"):
                connection.execute(f"DELETE FROM {table}")
            connection.execute("UPDATE life_archive SET revision = revision + 1, confirmed_revision = NULL, confirmed_at = NULL")


def delete_checkpoints(path, scope):
    if not path.exists():
        return
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("PRAGMA secure_delete = ON")
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table in ("writes", "checkpoints"):
            if table not in tables:
                continue
            if scope["all"]:
                connection.execute(f"DELETE FROM {table}")
            else:
                connection.executemany(
                    f"DELETE FROM {table} WHERE thread_id = ? OR substr(thread_id, 1, ?) = ?",
                    [(task, len(task) + 1, task + ":") for task in scope["tasks"]],
                )


def delete_backups(data_dir, scope):
    removed = 0
    for path in (data_dir / "backups").glob("backup-*"):
        if path.suffix not in (".zip", ".tmp") or not path.is_file():
            continue
        contains = True
        if not scope["all"] and path.suffix == ".zip":
            try:
                with ZipFile(path) as archive:
                    manifest = json.loads(archive.read("manifest.json"))
                contains = bool(set(manifest["branch_ids"]) & set(scope["branches"]))
            except (BadZipFile, KeyError, ValueError, TypeError):
                pass  # 无法识别的应用备份保守清理，避免残留已删除资料。
        if contains:
            path.unlink()
            removed += 1
    return removed


def finish_deletion(data_dir):
    journal = data_dir / "deletion.json"
    if not journal.exists():
        return
    scope = json.loads(journal.read_text(encoding="utf-8"))
    delete_checkpoints(data_dir / "workflow.sqlite", scope)
    delete_life(data_dir / "life.sqlite", scope)
    delete_backups(data_dir, scope)
    # 清理 WAL 中的旧页；逻辑删除不承诺擦除磁盘/系统备份里的历史副本。
    for name in ("life.sqlite", "workflow.sqlite"):
        path = data_dir / name
        if path.exists():
            with closing(sqlite3.connect(path)) as connection:
                busy = connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0]
                if busy:
                    raise RuntimeError("数据库仍被占用，删除清理将在重启后继续")
    journal.unlink()


def delete_data(data_dir, scope):
    journal = data_dir / "deletion.json"
    temporary = journal.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as file:
        json.dump(scope, file)
        file.flush()
        os.fsync(file.fileno())
    temporary.replace(journal)
    finish_deletion(data_dir)
