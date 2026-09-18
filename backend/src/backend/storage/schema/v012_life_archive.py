STATEMENTS = (
    """
    CREATE TABLE life_archive (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        revision INTEGER NOT NULL DEFAULT 1,
        confirmed_revision INTEGER,
        confirmed_at TEXT
    )
    """,
    """
    INSERT INTO life_archive (id) VALUES (1)
    """,
)