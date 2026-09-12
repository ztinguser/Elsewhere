STATEMENTS = (
    """
    CREATE TABLE events (
        id TEXT PRIMARY KEY NOT NULL,
        branch_id TEXT NOT NULL REFERENCES branches(id),
        position INTEGER NOT NULL CHECK (position >= 1),
        data TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending', 'validated', 'rejected')),
        created_at TEXT NOT NULL,
        UNIQUE (branch_id, position)
    )
    """,
)