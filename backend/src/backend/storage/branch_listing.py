import json


def list_branches(connection, branch_id: str | None = None) -> list[dict]:
    rows = connection.execute(
        """SELECT b.*,
                  json_extract(v.snapshot, '$.archive_revision') AS snapshot_revision,
                  a.revision AS archive_revision,
                  (SELECT COUNT(*) FROM simulation_stages WHERE branch_id = b.id) AS stage_count,
                  (SELECT end_time_text FROM simulation_stages WHERE branch_id = b.id
                   ORDER BY position DESC LIMIT 1) AS current_time_text,
                  (SELECT own.decision FROM simulation_choices own
                   JOIN simulation_stages s ON s.id = own.stage_id
                   JOIN simulation_choices origin ON origin.stage_id = s.source_stage_id
                   WHERE s.branch_id = b.id AND origin.id = b.fork_choice_id) AS fork_decision
           FROM branches b JOIN fact_versions v ON v.id = b.fact_version_id
           CROSS JOIN life_archive a
           WHERE (? IS NULL OR b.id = ?)
           ORDER BY b.created_at DESC, b.id""",
        (branch_id, branch_id),
    ).fetchall()
    result = []
    for row in rows:
        branch = dict(row)
        branch["assumptions"] = json.loads(branch["assumptions"])
        revision = branch.pop("snapshot_revision")
        current = branch.pop("archive_revision")
        branch["facts_outdated"] = revision != current if revision is not None else None
        result.append(branch)
    return result
