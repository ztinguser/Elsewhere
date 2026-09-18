import sqlite3

from backend.storage.life_archive import advance_archive_revision


def reorder_memories(
    connection: sqlite3.Connection,
    ids: list[str],
) -> None:
    current_ids = [
        row["id"]
        for row in connection.execute(
            """
            SELECT id FROM fact_nodes
            WHERE status = 'confirmed'
            ORDER BY position, id
            """
        )
    ]

    if len(ids) != len(current_ids) or set(ids) != set(current_ids):
        raise ValueError("节点列表已变化或包含重复项，请重新读取")

    if ids == current_ids:
        return

    connection.executemany(
        "UPDATE fact_nodes SET position = ? WHERE id = ?",
        [(position, memory_id) for position, memory_id in enumerate(ids, 1)],
    )
    advance_archive_revision(connection)