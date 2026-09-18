import json
import sqlite3
from datetime import date

from backend.storage.branches import create_branch
from backend.storage.life_archive import get_archive
from backend.storage.memories import get_memory
from backend.storage.versions import create_fact_version


def create_fork(
    connection: sqlite3.Connection,
    *,
    request_id: str,
    memory_id: str,
    alternative: str,
    expected_revision: int,
) -> str:
    input_data = {
        "memory_id": memory_id,
        "alternative": alternative,
        "expected_revision": expected_revision,
    }

    connection.execute(
        """
        INSERT INTO fork_requests (request_id, input_data)
        VALUES (?, ?)
        ON CONFLICT(request_id) DO NOTHING
        """,
        (request_id, json.dumps(input_data, ensure_ascii=False)),
    )
    saved = connection.execute(
        "SELECT input_data, branch_id FROM fork_requests WHERE request_id = ?",
        (request_id,),
    ).fetchone()

    if json.loads(saved["input_data"]) != input_data:
        raise ValueError("同一请求编号不能用于不同的创建参数")

    if saved["branch_id"] is not None:
        return saved["branch_id"]

    archive = get_archive(connection)
    if not archive["is_confirmed"] or archive["revision"] != expected_revision:
        raise ValueError("真实人生尚未确认存档或版本已变化，请重新检查")

    if get_memory(connection, memory_id) is None:
        raise ValueError("分叉回忆不存在")

    version_id = create_fact_version(connection)
    branch_id = create_branch(
        connection,
        fact_version_id=version_id,
        fork_fact_id=memory_id,
        alternative=alternative,
        target_date=date.today().isoformat(),
    )
    connection.execute(
        "UPDATE fork_requests SET branch_id = ? WHERE request_id = ?",
        (branch_id, request_id),
    )
    return branch_id