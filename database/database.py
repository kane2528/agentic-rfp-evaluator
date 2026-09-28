"""SQLite persistence for criteria and complete evaluation runs."""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

DEFAULT_CRITERIA = [
    ("Technical Capability", "Architecture, integrations, scalability, and technical fit.", 30.0, 10.0, 1),
    ("Implementation Plan", "Timeline, milestones, staffing, and delivery risk plan.", 20.0, 10.0, 1),
    ("Commercial Value", "Pricing clarity, total cost, and commercial assumptions.", 20.0, 10.0, 1),
    ("Security & Compliance", "Security controls, privacy, compliance, and auditability.", 20.0, 10.0, 1),
    ("Support & Experience", "Support model, relevant experience, and references.", 10.0, 10.0, 1),
]


def database_path() -> Path:
    return Path(os.getenv("RFP_DATABASE_PATH", "database/rfp_evaluator.db"))


@contextmanager
def get_connection(path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    db_path = Path(path) if path else database_path()
    if str(db_path) != ":memory:":
        db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(db_path), timeout=20)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database(path: str | Path | None = None) -> None:
    schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    with get_connection(path) as con:
        con.executescript(schema)
        # Upgrade databases created by the earlier classroom schema in place.
        run_columns = {row[1] for row in con.execute("PRAGMA table_info(rfp_runs)").fetchall()}
        if "result_json" not in run_columns:
            con.execute("ALTER TABLE rfp_runs ADD COLUMN result_json TEXT")


def seed_criteria(path: str | Path | None = None) -> None:
    with get_connection(path) as con:
        count = con.execute("SELECT COUNT(*) FROM evaluation_criteria").fetchone()[0]
        if not count:
            con.executemany(
                "INSERT INTO evaluation_criteria(name, description, weight, max_score, is_active) VALUES (?, ?, ?, ?, ?)",
                DEFAULT_CRITERIA,
            )


def list_criteria(active_only: bool = False, path: str | Path | None = None) -> list[dict[str, Any]]:
    with get_connection(path) as con:
        query = "SELECT criterion_id, name, description, weight, max_score, is_active FROM evaluation_criteria"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY criterion_id"
        return [dict(row) for row in con.execute(query).fetchall()]


def update_criteria(criteria: list[dict[str, Any]], path: str | Path | None = None) -> None:
    with get_connection(path) as con:
        for item in criteria:
            con.execute(
                "UPDATE evaluation_criteria SET name=?, description=?, weight=?, max_score=?, is_active=? WHERE criterion_id=?",
                (item["name"].strip(), item["description"], float(item["weight"]), float(item["max_score"]), int(bool(item["is_active"])), int(item["criterion_id"])),
            )


def create_run(run_id: str, created_at: str, status: str, criteria: list[dict[str, Any]], path: str | Path | None = None) -> None:
    with get_connection(path) as con:
        con.execute(
            "INSERT INTO rfp_runs(rfp_run_id, created_at, status, criteria_snapshot_json) VALUES (?, ?, ?, ?)",
            (run_id, created_at, status, json.dumps(criteria, ensure_ascii=False)),
        )


def update_run_status(run_id: str, status: str, error: str | None = None, path: str | Path | None = None) -> None:
    with get_connection(path) as con:
        con.execute("UPDATE rfp_runs SET status=?, error_message=? WHERE rfp_run_id=?", (status, error, run_id))


def save_run_export(run_id: str, export: dict[str, Any], path: str | Path | None = None) -> None:
    with get_connection(path) as con:
        con.execute("UPDATE rfp_runs SET result_json=? WHERE rfp_run_id=?", (json.dumps(export, ensure_ascii=False), run_id))


def persist_results(run_id: str, suppliers: list[dict[str, Any]], path: str | Path | None = None) -> None:
    """Atomically save the complete, ranked supplier payloads."""
    with get_connection(path) as con:
        con.executemany(
            """INSERT INTO supplier_results
            (rfp_run_id, supplier_name, submission_date, experience_rating, absolute_score, ppi, final_rank, result_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [(run_id, s["supplier_name"], s["submission_date"], s["experience_rating"], s["absolute_score"], s["ppi"], s["final_rank"], json.dumps(s, ensure_ascii=False)) for s in suppliers],
        )


def get_run(run_id: str, path: str | Path | None = None) -> dict[str, Any] | None:
    with get_connection(path) as con:
        row = con.execute("SELECT * FROM rfp_runs WHERE rfp_run_id=?", (run_id,)).fetchone()
        if row is None:
            return None
        run = dict(row)
        full_export = json.loads(run["result_json"]) if run.get("result_json") else None
        if full_export:
            if run.get("error_message"):
                full_export["error_message"] = run["error_message"]
            return full_export
        run.pop("result_json", None)
        run["criteria"] = json.loads(run.pop("criteria_snapshot_json"))
        run["suppliers"] = [json.loads(item[0]) for item in con.execute("SELECT result_json FROM supplier_results WHERE rfp_run_id=? ORDER BY final_rank", (run_id,)).fetchall()]
        return run


def list_runs(path: str | Path | None = None) -> list[dict[str, Any]]:
    with get_connection(path) as con:
        rows = con.execute("SELECT r.rfp_run_id, r.created_at, r.status, COUNT(s.supplier_name) AS supplier_count FROM rfp_runs r LEFT JOIN supplier_results s USING(rfp_run_id) GROUP BY r.rfp_run_id ORDER BY r.created_at DESC").fetchall()
        return [dict(row) for row in rows]
