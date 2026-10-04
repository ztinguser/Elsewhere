import hashlib
import io
import json
import os
import sqlite3
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from uuid import uuid4
from zipfile import ZipFile, ZIP_DEFLATED

from backend.storage.tasks import WORKFLOW_VERSION


# 明确列出业务表；未来加入设置或凭据表时不会被自动导出。
TABLES = (
    "life_archive", "drafts", "fragments", "fact_nodes", "fact_sources", "fact_versions",
    "branches", "fork_requests", "fork_plans", "simulation_stages", "simulation_choices",
    "events", "chapters", "chapter_versions", "paragraphs", "reading_positions", "tasks", "task_events",
)


@contextmanager
def snapshot(path):
    with closing(sqlite3.connect(path)) as source, closing(sqlite3.connect(":memory:")) as target:
        source.backup(target)
        yield target


def make_archive(data_dir, *, kind):
    with snapshot(data_dir / "workflow.sqlite") as connection:
        workflow = connection.serialize()
    with snapshot(data_dir / "life.sqlite") as connection:
        connection.row_factory = sqlite3.Row
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        branch_ids = [row[0] for row in connection.execute("SELECT id FROM branches")]
        if kind == "export":
            archive = {table: [dict(row) for row in connection.execute(f"SELECT * FROM {table}")]
                       for table in TABLES}
            files = {"archive.json": json.dumps(archive, ensure_ascii=False, indent=2).encode("utf-8")}
        else:
            files = {"life.sqlite": connection.serialize()}
    files["workflow.sqlite"] = workflow
    manifest = {
        "format": "elsewhere", "format_version": 1, "kind": kind,
        "created_at": datetime.now(UTC).isoformat(), "schema_version": version,
        "workflow_version": WORKFLOW_VERSION, "branch_ids": branch_ids,
        "files": {name: hashlib.sha256(content).hexdigest() for name, content in files.items()},
    }
    stream = io.BytesIO()
    with ZipFile(stream, "w", ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for name, content in files.items():
            archive.writestr(name, content)
    return stream.getvalue(), manifest


def save_backup(data_dir):
    content, manifest = make_archive(data_dir, kind="backup")
    directory = data_dir / "backups"
    directory.mkdir(exist_ok=True)
    name = f"backup-{uuid4().hex}.zip"
    path = directory / name
    temporary = path.with_suffix(".tmp")
    try:
        with temporary.open("wb") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return {"id": name, "created_at": manifest["created_at"], "size": len(content)}


def list_backups(data_dir):
    backups = []
    for path in (data_dir / "backups").glob("backup-*.zip"):
        if path.is_file():
            stat = path.stat()
            backups.append({"id": path.name, "size": stat.st_size,
                            "saved_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat()})
    return sorted(backups, key=lambda item: item["saved_at"], reverse=True)
