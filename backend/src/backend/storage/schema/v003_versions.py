STATEMENTS = (
    """
    CREATE TABLE fact_versions (
        id TEXT PRIMARY KEY NOT NULL,
        snapshot TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TRIGGER fact_versions_no_update
    BEFORE UPDATE ON fact_versions
    BEGIN
        SELECT RAISE(ABORT, 'Fact versions cannot be updated');
    END
    """,
)