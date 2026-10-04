STATEMENTS = (
    "ALTER TABLE chapters ADD COLUMN stage_id TEXT REFERENCES simulation_stages(id)",
    "ALTER TABLE chapters ADD COLUMN kind TEXT NOT NULL DEFAULT 'chapter' "
    "CHECK (kind IN ('chapter', 'today', 'retrospective'))",
    "CREATE UNIQUE INDEX idx_chapter_stage_kind ON chapters(stage_id, kind)",
    "ALTER TABLE chapter_versions ADD COLUMN outline TEXT NOT NULL DEFAULT '[]'",
    "ALTER TABLE chapter_versions ADD COLUMN review TEXT",
    "ALTER TABLE chapter_versions ADD COLUMN prompt_version TEXT",
    "ALTER TABLE chapter_versions ADD COLUMN generation TEXT",
)
