STATEMENTS = (
    """
    CREATE TABLE fragments (
        id TEXT PRIMARY KEY NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE fact_nodes (
        id TEXT PRIMARY KEY NOT NULL,
        content TEXT NOT NULL,
        kind TEXT NOT NULL CHECK (
            kind IN (
                'event', 'decision', 'feeling', 'constraint',
                'interpretation', 'judgment', 'inference'
            )
        ),
        status TEXT NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending', 'confirmed', 'disputed')),
        time_text TEXT,
        occurred_from TEXT,
        occurred_to TEXT,
        uncertainty TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        CHECK (occurred_from <= occurred_to)
    )
    """,
    """
    CREATE TABLE fact_sources (
        fact_id TEXT NOT NULL REFERENCES fact_nodes(id),
        fragment_id TEXT NOT NULL REFERENCES fragments(id),
        PRIMARY KEY (fact_id, fragment_id)
    )
    """,
    """
    CREATE INDEX idx_fact_sources_fragment
    ON fact_sources(fragment_id)
    """,
)