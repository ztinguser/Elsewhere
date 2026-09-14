STATEMENTS = (
    """
    ALTER TABLE fact_nodes
    ADD COLUMN revision INTEGER NOT NULL DEFAULT 1 CHECK (revision >= 1)
    """,
)