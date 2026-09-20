STATEMENTS = (
    """
    CREATE TABLE fork_plans (
        branch_id TEXT PRIMARY KEY NOT NULL REFERENCES branches(id),
        initial_result TEXT NOT NULL,
        final_result TEXT,
        answers TEXT NOT NULL DEFAULT '[]',
        status TEXT NOT NULL CHECK (
            status IN (
                'waiting_input', 'waiting_confirmation',
                'blocked', 'confirmed'
            )
        ),
        revision INTEGER NOT NULL DEFAULT 1 CHECK (revision >= 1),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
)