import json


def record_event(connection, task_id, event, data):
    connection.execute(
        "INSERT INTO task_events(task_id, event, data) VALUES (?, ?, ?)",
        (task_id, event, json.dumps(data, ensure_ascii=False)),
    )


def list_events(connection, task_id, after=0):
    rows = connection.execute(
        "SELECT * FROM task_events WHERE task_id = ? AND seq > ? ORDER BY seq LIMIT 100",
        (task_id, after),
    ).fetchall()
    return [{**dict(row), "data": json.loads(row["data"])} for row in rows]
