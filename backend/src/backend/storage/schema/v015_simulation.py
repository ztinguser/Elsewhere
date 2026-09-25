STATEMENTS = (
    """
    CREATE TABLE simulation_stages (
        id TEXT PRIMARY KEY NOT NULL,
        branch_id TEXT NOT NULL REFERENCES branches(id),
        position INTEGER NOT NULL CHECK (position >= 1),
        end_time_text TEXT NOT NULL,
        end_reason TEXT NOT NULL CHECK (end_reason IN ('choice', 'target')),
        review TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE (branch_id, position)
    )
    """,
    """
    CREATE TABLE simulation_choices (
        id TEXT PRIMARY KEY NOT NULL,
        stage_id TEXT NOT NULL UNIQUE REFERENCES simulation_stages(id),
        data TEXT NOT NULL,
        decision_input TEXT,
        decision TEXT,
        decided_at TEXT
    )
    """,
    "ALTER TABLE events ADD COLUMN stage_id TEXT REFERENCES simulation_stages(id)",
    "ALTER TABLE tasks ADD COLUMN error_message TEXT",
)