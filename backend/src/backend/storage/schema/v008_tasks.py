STATEMENTS = (
    """
    CREATE TABLE tasks (
        id TEXT PRIMARY KEY NOT NULL,
        kind TEXT NOT NULL
            CHECK (kind IN ('organize_memory', 'generate_branch')),
        branch_id TEXT REFERENCES branches(id),
        input_data TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'queued'
            CHECK (
                status IN (
                    'queued', 'running', 'waiting_input', 'interrupted',
                    'failed', 'cancelled', 'completed'
                )
            ),
        stage TEXT NOT NULL DEFAULT 'pending',
        retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
        error_code TEXT,
        workflow_version TEXT NOT NULL DEFAULT '1',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        CHECK (
            (kind = 'organize_memory' AND branch_id IS NULL)
            OR (kind = 'generate_branch' AND branch_id IS NOT NULL)
        )
    )
    """,
    """
    CREATE UNIQUE INDEX idx_tasks_active_branch
    ON tasks(branch_id)
    WHERE branch_id IS NOT NULL
        AND status IN ('queued', 'running', 'waiting_input', 'interrupted')
    """,
)