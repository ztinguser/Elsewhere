STATEMENTS = (
    "ALTER TABLE tasks ADD COLUMN execution_id TEXT",
    "UPDATE tasks SET execution_id = lower(hex(randomblob(16)))",
    # 旧版尚无 LangGraph 检查点，可从业务记录建立新版检查点。
    "UPDATE tasks SET workflow_version = '2' WHERE workflow_version = '1'",
    "ALTER TABLE chapter_versions ADD COLUMN draft_key TEXT",
    "CREATE UNIQUE INDEX idx_chapter_draft_key ON chapter_versions(draft_key) WHERE draft_key IS NOT NULL",
)
