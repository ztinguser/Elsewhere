STATEMENTS = (
    """
    CREATE TABLE fork_requests (
        request_id TEXT PRIMARY KEY NOT NULL,
        input_data TEXT NOT NULL,
        branch_id TEXT UNIQUE REFERENCES branches(id)
    )
    """,
)