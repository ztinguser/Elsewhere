import sqlite3


def reorder_memories(
    connection: sqlite3.Connection,
    ids: list[str],
) -> None:
    current_ids = {
        row["id"]
        for row in connection.execute(
            "SELECT id FROM fact_nodes WHERE status = 'confirmed'"
        )
    }

    if len(ids) != len(current_ids) or set(ids) != current_ids:
        raise ValueError("节点列表已变化或包含重复项，请重新读取")

    connection.executemany(
        "UPDATE fact_nodes SET position = ? WHERE id = ?",
        [(position, memory_id) for position, memory_id in enumerate(ids, 1)],
    )