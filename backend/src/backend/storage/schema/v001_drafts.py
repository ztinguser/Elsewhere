STATEMENTS = (
    """
    CREATE TABLE drafts (
        id TEXT PRIMARY KEY NOT NULL,
        content TEXT NOT NULL DEFAULT '',
        revision INTEGER NOT NULL DEFAULT 1 CHECK (revision >= 1),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
)