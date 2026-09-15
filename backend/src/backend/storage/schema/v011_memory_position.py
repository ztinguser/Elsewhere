STATEMENTS = (
    """
    ALTER TABLE fact_nodes
    ADD COLUMN position INTEGER NOT NULL DEFAULT 0
    """,
    """
    WITH ordered AS (
        SELECT id, ROW_NUMBER() OVER (ORDER BY created_at, id) AS number
        FROM fact_nodes
    )
    UPDATE fact_nodes
    SET position = (
        SELECT number FROM ordered WHERE ordered.id = fact_nodes.id
    )
    """,
)