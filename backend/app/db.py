"""
Local SQLite storage: every time a story is submitted through /generate,
the full result (extraction, scoring, generated requirements, validation)
is saved here automatically, so you can look back at anything you've ever
generated without re-running it.

No setup needed -- this uses Python's built-in sqlite3 module (no extra
service to install or run) and creates a single file, parg_history.db, in
the backend folder the first time the server starts.
"""
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone

from . import config

DB_PATH = os.path.join(config.BASE_DIR, "parg_history.db")
_lock = threading.Lock()


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Creates the tables if they don't already exist. Safe to call every
    time the server starts -- it never touches existing data."""
    with _lock, _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                user_story TEXT NOT NULL,
                process_concept TEXT NOT NULL,
                ontology_mapping TEXT NOT NULL,
                domain_entity TEXT,
                model_confidence REAL NOT NULL,
                ontology_similarity REAL NOT NULL,
                hybrid_score REAL NOT NULL,
                selection_status TEXT NOT NULL,
                low_confidence INTEGER NOT NULL,
                actor_text TEXT, actor_confidence REAL,
                action_text TEXT, action_confidence REAL,
                condition_text TEXT, condition_confidence REAL,
                outcome_text TEXT, outcome_confidence REAL,
                validation_status TEXT NOT NULL,
                validation_issues_json TEXT NOT NULL,
                session_processes_covered INTEGER,
                session_total_processes INTEGER,
                warnings_json TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS requirements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id INTEGER NOT NULL,
                step TEXT NOT NULL,
                step_purpose TEXT,
                action_verb TEXT NOT NULL,
                text TEXT NOT NULL,
                repaired INTEGER NOT NULL,
                repair_actions_json TEXT NOT NULL,
                requires_review INTEGER NOT NULL,
                unrepaired_issues_json TEXT NOT NULL,
                FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_req_submission ON requirements(submission_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sub_created ON submissions(created_at)")

        # Migration: if parg_history.db already existed from before the
        # domain_entity column was added, CREATE TABLE IF NOT EXISTS above
        # is a no-op on it -- add the column here so old databases keep
        # working instead of breaking on the next save/export.
        existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(submissions)").fetchall()}
        if "domain_entity" not in existing_cols:
            conn.execute("ALTER TABLE submissions ADD COLUMN domain_entity TEXT")


def save_submission(result: dict) -> int:
    """Saves one /generate result (the same dict returned to the browser)
    and returns the new submission's database id."""
    ner = result["ner"]
    scoring = result["scoring"]
    validation = result["validation"]

    with _lock, _connect() as conn:
        cur = conn.execute(
            """INSERT INTO submissions (
                created_at, user_story, process_concept, ontology_mapping, domain_entity,
                model_confidence, ontology_similarity, hybrid_score, selection_status, low_confidence,
                actor_text, actor_confidence, action_text, action_confidence,
                condition_text, condition_confidence, outcome_text, outcome_confidence,
                validation_status, validation_issues_json,
                session_processes_covered, session_total_processes, warnings_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                datetime.now(timezone.utc).isoformat(),
                result["user_story"], result["process_concept"], result["ontology_mapping"],
                result.get("domain_entity", ""),
                scoring["model_confidence"], scoring["ontology_similarity"], scoring["hybrid_score"],
                scoring["selection_status"], int(scoring["low_confidence"]),
                ner["actor"]["text"], ner["actor"]["confidence"],
                ner["action"]["text"], ner["action"]["confidence"],
                ner["condition"]["text"], ner["condition"]["confidence"],
                ner["outcome"]["text"], ner["outcome"]["confidence"],
                validation["status"], json.dumps(validation["issues"]),
                validation["session_processes_covered"], validation["session_total_processes"],
                json.dumps(result["warnings"]),
            ),
        )
        submission_id = cur.lastrowid
        for r in result["requirements"]:
            conn.execute(
                """INSERT INTO requirements (
                    submission_id, step, step_purpose, action_verb, text,
                    repaired, repair_actions_json, requires_review, unrepaired_issues_json
                ) VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    submission_id, r["step"], r.get("step_purpose", ""), r["action_verb"], r["text"],
                    int(r.get("repaired", False)), json.dumps(r.get("repair_actions", [])),
                    int(r.get("requires_review", False)), json.dumps(r.get("unrepaired_issues", [])),
                ),
            )
        return submission_id


def list_submissions(limit: int = 50, offset: int = 0) -> list:
    """Newest-first summary list, for the History page."""
    with _connect() as conn:
        rows = conn.execute(
            """SELECT id, created_at, user_story, process_concept, hybrid_score,
                      selection_status, validation_status
               FROM submissions ORDER BY id DESC LIMIT ? OFFSET ?""",
            (limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]


def count_submissions() -> int:
    with _connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]


def get_submission(submission_id: int) -> dict | None:
    """Full stored detail for one submission, reshaped back into the same
    structure /generate returns, so the frontend can reuse its existing
    display components unchanged."""
    with _connect() as conn:
        sub = conn.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,)).fetchone()
        if sub is None:
            return None
        sub = dict(sub)
        reqs = conn.execute(
            "SELECT * FROM requirements WHERE submission_id = ? ORDER BY id", (submission_id,)
        ).fetchall()

    requirements = [{
        "step": r["step"],
        "step_purpose": r["step_purpose"] or "",
        "action_verb": r["action_verb"],
        "text": r["text"],
        "repaired": bool(r["repaired"]),
        "repair_actions": json.loads(r["repair_actions_json"]),
        "requires_review": bool(r["requires_review"]),
        "unrepaired_issues": json.loads(r["unrepaired_issues_json"]),
    } for r in reqs]

    return {
        "id": sub["id"],
        "created_at": sub["created_at"],
        "user_story": sub["user_story"],
        "process_concept": sub["process_concept"],
        "ontology_mapping": sub["ontology_mapping"],
        "domain_entity": sub["domain_entity"] or "",
        "ner": {
            "actor": {"text": sub["actor_text"], "confidence": sub["actor_confidence"], "low_confidence": False},
            "action": {"text": sub["action_text"], "confidence": sub["action_confidence"], "low_confidence": False},
            "condition": {"text": sub["condition_text"], "confidence": sub["condition_confidence"], "low_confidence": False},
            "outcome": {"text": sub["outcome_text"], "confidence": sub["outcome_confidence"], "low_confidence": False},
        },
        "scoring": {
            "model_confidence": sub["model_confidence"],
            "ontology_similarity": sub["ontology_similarity"],
            "hybrid_score": sub["hybrid_score"],
            "alpha": config.ALPHA, "beta": config.BETA, "confidence_threshold": config.CONFIDENCE_THRESHOLD,
            "selection_status": sub["selection_status"],
            "low_confidence": bool(sub["low_confidence"]),
        },
        "requirements": requirements,
        "validation": {
            "status": sub["validation_status"],
            "issues": json.loads(sub["validation_issues_json"]),
            "checks_performed": ["grammar", "duplicate", "ambiguous_terms", "semantic_relevance", "traceability"],
            "duplicate_within_story": False,
            "ambiguous_terms_found": [],
            "extraction_summary": {
                "actor_found": bool(sub["actor_text"]), "action_found": bool(sub["action_text"]),
                "condition_found": bool(sub["condition_text"]), "outcome_found": bool(sub["outcome_text"]),
            },
            "generic_fallback_count": 0,
            "session_processes_covered": sub["session_processes_covered"] or 0,
            "session_total_processes": sub["session_total_processes"] or 0,
            "session_coverage_pct": round(
                100 * (sub["session_processes_covered"] or 0) / max(sub["session_total_processes"] or 1, 1), 2
            ),
            "note": "Restored from saved history -- session coverage reflects the value at the time this "
                    "story was originally submitted, not the current session.",
        },
        "warnings": json.loads(sub["warnings_json"]),
    }


def delete_submission(submission_id: int) -> bool:
    with _lock, _connect() as conn:
        cur = conn.execute("DELETE FROM submissions WHERE id = ?", (submission_id,))
        return cur.rowcount > 0
