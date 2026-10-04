STATEMENTS = (
    "ALTER TABLE tasks ADD COLUMN waiting_reason TEXT",
    "ALTER TABLE tasks ADD COLUMN waiting_object_id TEXT",
    "ALTER TABLE tasks ADD COLUMN retry_of TEXT REFERENCES tasks(id)",
    "CREATE UNIQUE INDEX idx_tasks_retry ON tasks(retry_of) WHERE retry_of IS NOT NULL",
    """
    CREATE TABLE task_events (
        seq INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
        event TEXT NOT NULL,
        data TEXT NOT NULL
    )
    """,
    "CREATE INDEX idx_task_events_task ON task_events(task_id, seq)",
    *(
        f"""
        CREATE TRIGGER task_event_{name} AFTER {action} ON tasks
        BEGIN
            INSERT INTO task_events(task_id, event, data)
            VALUES (NEW.id, 'task', json_object(
                'id', NEW.id, 'branch_id', NEW.branch_id,
                'status', NEW.status, 'stage', NEW.stage,
                'waiting_reason', NEW.waiting_reason,
                'waiting_object_id', NEW.waiting_object_id,
                'error_code', NEW.error_code, 'error_message', NEW.error_message,
                'updated_at', NEW.updated_at
            ));
        END
        """
        for name, action in (
            ("insert", "INSERT"),
            ("update", "UPDATE OF status, stage, waiting_reason, error_code"),
        )
    ),
)
