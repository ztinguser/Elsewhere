STATEMENTS = (
    """
    CREATE TABLE branches (
        id TEXT PRIMARY KEY NOT NULL,
        parent_id TEXT REFERENCES branches(id),
        fact_version_id TEXT NOT NULL REFERENCES fact_versions(id),
        fork_fact_id TEXT NOT NULL,
        alternative TEXT NOT NULL,
        target_date TEXT NOT NULL,
        assumptions TEXT NOT NULL DEFAULT '[]',
        status TEXT NOT NULL DEFAULT 'draft'
            CHECK (status IN ('draft', 'ready', 'completed')),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TRIGGER branches_fixed_basis
    BEFORE UPDATE OF fact_version_id, fork_fact_id, parent_id ON branches
    BEGIN
        SELECT RAISE(ABORT, 'Branch basis cannot be changed');
    END
    """,
)