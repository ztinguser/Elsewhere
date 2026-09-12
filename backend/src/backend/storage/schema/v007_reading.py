STATEMENTS = (
    """
    CREATE TABLE reading_positions (
        branch_id TEXT PRIMARY KEY NOT NULL REFERENCES branches(id),
        paragraph_id TEXT NOT NULL REFERENCES paragraphs(id),
        char_offset INTEGER NOT NULL DEFAULT 0 CHECK (char_offset >= 0),
        updated_at TEXT NOT NULL
    )
    """,
)