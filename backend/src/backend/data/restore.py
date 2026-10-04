"""将备份恢复到新的空目录；停止后端后使用，不覆盖现有档案。"""
import argparse
import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from zipfile import ZipFile

from backend.storage.migrations import MIGRATIONS
from backend.storage.tasks import WORKFLOW_VERSION


def restore_backup(backup: Path, destination: Path):
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("恢复目标必须是新的空目录")
    with ZipFile(backup) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        if (manifest.get("format") != "elsewhere" or manifest.get("format_version") != 1
                or manifest.get("kind") != "backup"):
            raise ValueError("请选择 Elsewhere 数据库备份，不能用 JSON 导出替代")
        if (manifest["schema_version"] > len(MIGRATIONS)
                or manifest["workflow_version"] != WORKFLOW_VERSION):
            raise ValueError("备份版本不兼容，请使用对应版本的程序")
        files = {name: archive.read(name) for name in ("life.sqlite", "workflow.sqlite")}
        for name, content in files.items():
            if hashlib.sha256(content).hexdigest() != manifest["files"][name]:
                raise ValueError("备份校验失败，文件内容已变化")
    destination.mkdir(parents=True, exist_ok=True)
    try:
        for name, content in files.items():
            path = destination / name
            path.write_bytes(content)
            with closing(sqlite3.connect(path)) as connection:
                if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                    raise ValueError("备份数据库完整性检查失败")
                if connection.execute("PRAGMA foreign_key_check").fetchall():
                    raise ValueError("备份数据库关联检查失败")
                if name == "life.sqlite" and connection.execute("PRAGMA user_version").fetchone()[0] != manifest["schema_version"]:
                    raise ValueError("备份数据库版本与清单不一致")
    except Exception:
        for name in files:
            for suffix in ("", "-wal", "-shm"):
                (destination / (name + suffix)).unlink(missing_ok=True)
        raise
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", type=Path)
    parser.add_argument("--destination", type=Path, required=True)
    arguments = parser.parse_args()
    restore_backup(arguments.backup, arguments.destination)
    print(f"备份已校验并恢复到：{arguments.destination.resolve()}")


if __name__ == "__main__":
    main()
