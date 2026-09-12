STATEMENTS = (
    """
    CREATE TABLE chapters (
        id TEXT PRIMARY KEY NOT NULL,
        branch_id TEXT NOT NULL REFERENCES branches(id),
        position INTEGER NOT NULL CHECK (position >= 1),
        created_at TEXT NOT NULL,
        UNIQUE (branch_id, position)
    )
    """,
    """
    CREATE TABLE chapter_versions (
        id TEXT PRIMARY KEY NOT NULL,
        chapter_id TEXT NOT NULL REFERENCES chapters(id),
        revision INTEGER NOT NULL CHECK (revision >= 1),
        title TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'draft'
            CHECK (
                status IN (
                    'draft', 'reviewed', 'published',
                    'superseded', 'rejected'
                )
            ),
        created_at TEXT NOT NULL,
        UNIQUE (chapter_id, revision)
    )
    """,
    """
    CREATE UNIQUE INDEX idx_chapter_published
    ON chapter_versions(chapter_id)
    WHERE status = 'published'
    """,
    """
    CREATE TABLE paragraphs (
        id TEXT PRIMARY KEY NOT NULL,
        version_id TEXT NOT NULL REFERENCES chapter_versions(id),
        position INTEGER NOT NULL CHECK (position >= 1),
        content TEXT NOT NULL,
        UNIQUE (version_id, position)
    )
    """,
)