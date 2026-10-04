STATEMENTS = (
    "ALTER TABLE branches ADD COLUMN fork_choice_id TEXT REFERENCES simulation_choices(id)",
    "ALTER TABLE simulation_stages ADD COLUMN source_stage_id TEXT REFERENCES simulation_stages(id)",
    "ALTER TABLE chapter_versions ADD COLUMN source_version_id TEXT REFERENCES chapter_versions(id)",
)
