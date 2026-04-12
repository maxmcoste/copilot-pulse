"""SQLite database for org structure and Copilot usage data."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path.home() / ".copilot-pulse" / "orgdata.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
    employee_id     TEXT PRIMARY KEY,
    matricola       TEXT,
    github_id       TEXT,
    name            TEXT,
    surname         TEXT,
    email           TEXT,
    email_work      TEXT,
    gender          TEXT,
    age             INTEGER,
    date_of_birth   TEXT,
    company         TEXT,
    company_ref_id  TEXT,
    location_country TEXT,
    location        TEXT,
    location_id     TEXT,
    position_title  TEXT,
    business_title  TEXT,
    job_profile     TEXT,
    job_family      TEXT,
    job_code        TEXT,
    job_title       TEXT,
    job_level       TEXT,
    job_category    TEXT,
    management_level TEXT,
    worker_type     TEXT,
    employee_type   TEXT,
    contract_type   TEXT,
    time_type       TEXT,
    fte             REAL DEFAULT 1.0,
    is_manager      INTEGER,
    original_hire_date TEXT,
    continuous_service_date TEXT,
    company_service_date TEXT,
    length_of_service TEXT,
    time_in_position TEXT,
    cdc_code        TEXT,
    cost_center_id  TEXT,
    supervisory_org TEXT,
    supervisory_org_id TEXT,
    top_level_sup_org TEXT,
    sup_org_level_2 TEXT,
    sup_org_level_3 TEXT,
    sup_org_level_4 TEXT,
    sup_org_level_5 TEXT,
    sup_org_level_6 TEXT,
    sup_org_level_7 TEXT,
    sup_org_level_8 TEXT,
    sup_org_level_9 TEXT,
    sup_org_level_10 TEXT,
    hr_business_partner TEXT,
    hr_director     TEXT
);

CREATE INDEX IF NOT EXISTS idx_employees_github_id ON employees(github_id);
CREATE INDEX IF NOT EXISTS idx_employees_matricola ON employees(matricola);
CREATE INDEX IF NOT EXISTS idx_employees_email_work ON employees(email_work);
CREATE INDEX IF NOT EXISTS idx_employees_sup_org_6 ON employees(sup_org_level_6);
CREATE INDEX IF NOT EXISTS idx_employees_job_family ON employees(job_family);
CREATE INDEX IF NOT EXISTS idx_employees_age ON employees(age);

CREATE TABLE IF NOT EXISTS copilot_usage (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    github_login                TEXT NOT NULL,
    report_date                 TEXT,
    period                      TEXT DEFAULT '28-day',
    completions_suggestions     INTEGER DEFAULT 0,
    completions_acceptances     INTEGER DEFAULT 0,
    completions_lines_suggested INTEGER DEFAULT 0,
    completions_lines_accepted  INTEGER DEFAULT 0,
    chat_turns                  INTEGER DEFAULT 0,
    chat_insertion_events       INTEGER DEFAULT 0,
    chat_copy_events            INTEGER DEFAULT 0,
    agent_turns                 INTEGER DEFAULT 0,
    cli_turns                   INTEGER DEFAULT 0,
    fetched_at                  TEXT DEFAULT (datetime('now')),
    UNIQUE(github_login, report_date, period)
);

CREATE INDEX IF NOT EXISTS idx_usage_github ON copilot_usage(github_login);
CREATE INDEX IF NOT EXISTS idx_usage_date ON copilot_usage(report_date);

CREATE TABLE IF NOT EXISTS github_id_mappings (
    employee_id TEXT NOT NULL,
    github_id   TEXT NOT NULL,
    match_method TEXT DEFAULT 'manual',
    confidence  REAL DEFAULT 1.0,
    created_at  TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (employee_id, github_id)
);
"""

# Age range buckets as a SQL CASE expression
AGE_RANGE_CASE = """
    CASE
        WHEN e.age IS NULL THEN 'Unknown'
        WHEN e.age < 25 THEN '<25'
        WHEN e.age < 30 THEN '25-29'
        WHEN e.age < 35 THEN '30-34'
        WHEN e.age < 40 THEN '35-39'
        WHEN e.age < 45 THEN '40-44'
        WHEN e.age < 50 THEN '45-49'
        WHEN e.age < 55 THEN '50-54'
        WHEN e.age < 60 THEN '55-59'
        ELSE '60+'
    END
"""


class OrgDatabase:
    """SQLite database for org structure and Copilot usage data.

    Args:
        db_path: Path to the SQLite database file.
    """

    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self) -> None:
        """Create tables and indexes if they don't exist."""
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    # ------------------------------------------------------------------
    # Import employees from Excel
    # ------------------------------------------------------------------

    def import_employees(self, employees: list[dict[str, Any]], replace: bool = True) -> int:
        """Import employee records into the database.

        Args:
            employees: List of employee dicts (from OrgDataLoader).
            replace: If True, clear existing data first.

        Returns:
            Number of records imported.
        """
        if replace:
            self._conn.execute("DELETE FROM employees")

        cols = [
            "employee_id", "matricola", "github_id", "name", "surname",
            "email", "email_work", "gender", "age", "date_of_birth",
            "company", "company_ref_id", "location_country", "location", "location_id",
            "position_title", "business_title", "job_profile", "job_family",
            "job_code", "job_title", "job_level", "job_category", "management_level",
            "worker_type", "employee_type", "contract_type", "time_type", "fte",
            "is_manager", "original_hire_date", "continuous_service_date",
            "company_service_date", "length_of_service", "time_in_position",
            "cdc_code", "cost_center_id", "supervisory_org", "supervisory_org_id",
            "top_level_sup_org", "sup_org_level_2", "sup_org_level_3",
            "sup_org_level_4", "sup_org_level_5", "sup_org_level_6",
            "sup_org_level_7", "sup_org_level_8", "sup_org_level_9",
            "sup_org_level_10", "hr_business_partner", "hr_director",
        ]
        placeholders = ", ".join(["?"] * len(cols))
        col_names = ", ".join(cols)
        sql = f"INSERT OR REPLACE INTO employees ({col_names}) VALUES ({placeholders})"

        count = 0
        for emp in employees:
            values = []
            for col in cols:
                val = emp.get(col)
                if col == "is_manager":
                    val = 1 if val else (0 if val is False else None)
                if col in ("date_of_birth", "original_hire_date", "continuous_service_date", "company_service_date"):
                    val = str(val) if val else None
                values.append(val)
            self._conn.execute(sql, values)
            count += 1

        self._conn.commit()
        logger.info("Imported %d employees", count)
        return count

    def merge_employees(self, employees: list[dict[str, Any]]) -> dict[str, int]:
        """Merge employee records preserving existing github_id mappings.

        Uses matricola as the join key. For employees already in the DB,
        all fields are updated EXCEPT github_id is preserved when the
        incoming record has it blank but the DB has a non-empty value.

        Employees in the DB but not in the new file are kept (not deleted).

        Returns:
            Dict with counts: imported, updated, preserved_mappings.
        """
        # Build lookup of existing github_id by matricola
        existing = {}
        rows = self._conn.execute(
            "SELECT matricola, github_id FROM employees "
            "WHERE matricola IS NOT NULL AND matricola != ''"
        ).fetchall()
        for row in rows:
            existing[row["matricola"]] = row["github_id"] or ""

        cols = [
            "employee_id", "matricola", "github_id", "name", "surname",
            "email", "email_work", "gender", "age", "date_of_birth",
            "company", "company_ref_id", "location_country", "location", "location_id",
            "position_title", "business_title", "job_profile", "job_family",
            "job_code", "job_title", "job_level", "job_category", "management_level",
            "worker_type", "employee_type", "contract_type", "time_type", "fte",
            "is_manager", "original_hire_date", "continuous_service_date",
            "company_service_date", "length_of_service", "time_in_position",
            "cdc_code", "cost_center_id", "supervisory_org", "supervisory_org_id",
            "top_level_sup_org", "sup_org_level_2", "sup_org_level_3",
            "sup_org_level_4", "sup_org_level_5", "sup_org_level_6",
            "sup_org_level_7", "sup_org_level_8", "sup_org_level_9",
            "sup_org_level_10", "hr_business_partner", "hr_director",
        ]
        placeholders = ", ".join(["?"] * len(cols))
        col_names = ", ".join(cols)
        sql = f"INSERT OR REPLACE INTO employees ({col_names}) VALUES ({placeholders})"

        inserted = 0
        updated = 0
        preserved = 0

        for emp in employees:
            matricola = str(emp.get("matricola") or "").strip()
            incoming_gh = str(emp.get("github_id") or "").strip()

            # Preserve existing github_id if incoming is blank
            if matricola and matricola in existing:
                updated += 1
                db_gh = existing[matricola]
                if not incoming_gh and db_gh:
                    emp = dict(emp)  # shallow copy to avoid mutating original
                    emp["github_id"] = db_gh
                    preserved += 1
            else:
                inserted += 1

            values = []
            for col in cols:
                val = emp.get(col)
                if col == "is_manager":
                    val = 1 if val else (0 if val is False else None)
                if col in ("date_of_birth", "original_hire_date",
                           "continuous_service_date", "company_service_date"):
                    val = str(val) if val else None
                values.append(val)
            self._conn.execute(sql, values)

        self._conn.commit()
        logger.info(
            "Merged employees: %d inserted, %d updated, %d github_id preserved",
            inserted, updated, preserved,
        )
        return {"imported": inserted + updated, "updated": updated,
                "inserted": inserted, "preserved_mappings": preserved}

    # ------------------------------------------------------------------
    # Store Copilot usage data
    # ------------------------------------------------------------------

    def store_usage(self, records: list[dict[str, Any]], period: str = "28-day") -> int:
        """Store Copilot usage records from the GitHub API.

        Args:
            records: List of user usage dicts.
            period: Report period ('1-day' or '28-day').

        Returns:
            Number of records stored.
        """
        sql = """
            INSERT OR REPLACE INTO copilot_usage (
                github_login, report_date, period,
                completions_suggestions, completions_acceptances,
                completions_lines_suggested, completions_lines_accepted,
                chat_turns, chat_insertion_events, chat_copy_events,
                agent_turns, cli_turns
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        count = 0
        for r in records:
            self._conn.execute(sql, (
                r.get("github_login", ""),
                str(r.get("date", "")) or "",
                period,
                r.get("completions_suggestions", 0),
                r.get("completions_acceptances", 0),
                r.get("completions_lines_suggested", 0),
                r.get("completions_lines_accepted", 0),
                r.get("chat_turns", 0),
                r.get("chat_insertion_events", 0),
                r.get("chat_copy_events", 0),
                r.get("agent_turns", 0),
                r.get("cli_turns", 0),
            ))
            count += 1

        self._conn.commit()
        logger.info("Stored %d usage records", count)
        return count

    # ------------------------------------------------------------------
    # GitHub ID mapping
    # ------------------------------------------------------------------

    def set_github_id(self, employee_id: str, github_id: str, method: str = "manual") -> None:
        """Map an employee to a GitHub ID.

        Args:
            employee_id: Employee ID from org structure.
            github_id: GitHub username.
            method: How the mapping was determined.
        """
        self._conn.execute(
            "UPDATE employees SET github_id = ? WHERE employee_id = ?",
            (github_id, employee_id),
        )
        self._conn.execute(
            "INSERT OR REPLACE INTO github_id_mappings (employee_id, github_id, match_method) VALUES (?, ?, ?)",
            (employee_id, github_id, method),
        )
        self._conn.commit()

    def auto_map_by_email(
        self,
        github_users: list[str],
        email_pattern: str = "{name}.{surname}",
        duplicate_strategy: str = "skip",
    ) -> list[dict[str, str]]:
        """Try to match GitHub users to employees by email pattern.

        Builds a candidate email local-part from employee name/surname using
        the given *email_pattern* and compares it against the GitHub login.

        Args:
            github_users: List of GitHub logins to try matching.
            email_pattern: Pattern for generating email local-parts from employee
                data.  Supported placeholders: ``{name}``, ``{surname}``,
                ``{name1}`` (first letter of name).
                Examples: ``{name}.{surname}``, ``{surname}.{name}``,
                ``{name1}.{surname}``.
            duplicate_strategy: How to handle multiple employees that produce
                the same email local-part.
                * ``"skip"``  — skip the match (safe default)
                * ``"seq2"``  — try appending a 2-digit sequence number
                  (e.g. ``name.surname.01``) to disambiguate
                * ``"first"`` — pick the first employee found

        Returns:
            List of successful matches with employee_id, github_login, email.
        """
        matches = []
        for login in github_users:
            # Try exact match on github_id first
            row = self._conn.execute(
                "SELECT employee_id, email_work FROM employees WHERE LOWER(github_id) = LOWER(?)",
                (login,),
            ).fetchone()
            if row:
                continue  # Already mapped

            # Try matching login against email local part
            row = self._conn.execute(
                "SELECT employee_id, email_work FROM employees WHERE LOWER(SUBSTR(email_work, 1, INSTR(email_work, '@') - 1)) = LOWER(?)",
                (login,),
            ).fetchone()
            if row:
                self.set_github_id(row["employee_id"], login, method="email_match")
                matches.append({
                    "employee_id": row["employee_id"],
                    "github_login": login,
                    "email": row["email_work"],
                })
                continue

            # Try matching with dots/hyphens normalized
            normalized = login.replace("-", ".").replace("_", ".")
            row = self._conn.execute(
                "SELECT employee_id, email_work FROM employees WHERE LOWER(REPLACE(REPLACE(SUBSTR(email_work, 1, INSTR(email_work, '@') - 1), '-', '.'), '_', '.')) = LOWER(?)",
                (normalized,),
            ).fetchone()
            if row:
                self.set_github_id(row["employee_id"], login, method="email_normalized")
                matches.append({
                    "employee_id": row["employee_id"],
                    "github_login": login,
                    "email": row["email_work"],
                })
                continue

            # Try configurable name/surname pattern matching
            match_result = self._match_by_pattern(
                login, email_pattern, duplicate_strategy,
            )
            if match_result:
                matches.append(match_result)

        self._conn.commit()
        logger.info("Auto-mapped %d GitHub users to employees", len(matches))
        return matches

    def _build_local_part(self, name: str, surname: str, pattern: str) -> str:
        """Build an email local-part from employee name/surname using pattern."""
        return (
            pattern
            .replace("{name}", name)
            .replace("{surname}", surname)
            .replace("{name1}", name[:1] if name else "")
        ).lower()

    def _match_by_pattern(
        self,
        login: str,
        email_pattern: str,
        duplicate_strategy: str,
    ) -> dict[str, str] | None:
        """Match a GitHub login against employees using the configured pattern.

        Generates the expected local-part for each candidate and compares it
        to the (normalised) login.
        """
        normalized_login = login.replace("-", ".").replace("_", ".").lower()

        # Strip a trailing 2-digit sequence number for seq2 strategy
        base_login = normalized_login
        seq_suffix = ""
        if duplicate_strategy == "seq2" and len(normalized_login) > 3:
            # Check if login ends with .NN (2-digit seq)
            if normalized_login[-3] == "." and normalized_login[-2:].isdigit():
                base_login = normalized_login[:-3]
                seq_suffix = normalized_login[-2:]

        # Fetch candidate employees whose name/surname could match
        # We query broadly then filter in Python for pattern flexibility
        parts = base_login.split(".")
        if len(parts) < 2 and "{name1}" not in email_pattern:
            return None

        rows = self._conn.execute(
            "SELECT employee_id, name, surname, email_work FROM employees "
            "WHERE github_id IS NULL OR github_id = ''",
        ).fetchall()

        candidates = []
        for row in rows:
            emp_name = (row["name"] or "").strip()
            emp_surname = (row["surname"] or "").strip()
            if not emp_name or not emp_surname:
                continue

            local_part = self._build_local_part(emp_name, emp_surname, email_pattern)
            if local_part == base_login:
                candidates.append(row)

        if not candidates:
            return None

        if len(candidates) == 1:
            row = candidates[0]
            self.set_github_id(row["employee_id"], login, method="pattern_match")
            return {
                "employee_id": row["employee_id"],
                "github_login": login,
                "email": row["email_work"],
                "matched_name": f"{row['name']} {row['surname']}",
            }

        # Multiple candidates — apply duplicate strategy
        if duplicate_strategy == "skip":
            logger.info(
                "Skipping login %s — %d duplicate candidates", login, len(candidates),
            )
            return None

        if duplicate_strategy == "first":
            row = candidates[0]
            self.set_github_id(row["employee_id"], login, method="pattern_first")
            return {
                "employee_id": row["employee_id"],
                "github_login": login,
                "email": row["email_work"],
                "matched_name": f"{row['name']} {row['surname']}",
            }

        if duplicate_strategy == "seq2":
            # If login had a .NN suffix, use it as 1-based index
            if seq_suffix:
                idx = int(seq_suffix) - 1
                # Sort candidates deterministically by employee_id
                candidates.sort(key=lambda r: r["employee_id"])
                if 0 <= idx < len(candidates):
                    row = candidates[idx]
                    self.set_github_id(row["employee_id"], login, method="pattern_seq")
                    return {
                        "employee_id": row["employee_id"],
                        "github_login": login,
                        "email": row["email_work"],
                        "matched_name": f"{row['name']} {row['surname']}",
                    }
            return None

        return None

    # ------------------------------------------------------------------
    # Queries — org structure
    # ------------------------------------------------------------------

    def employee_count(self) -> int:
        """Total number of employees in the database."""
        return self._conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]

    def mapped_count(self) -> int:
        """Number of employees with a GitHub ID assigned."""
        return self._conn.execute(
            "SELECT COUNT(*) FROM employees WHERE github_id IS NOT NULL AND github_id != ''"
        ).fetchone()[0]

    def org_summary(self) -> dict[str, Any]:
        """Get summary statistics of the org structure."""
        result: dict[str, Any] = {
            "total_employees": self.employee_count(),
            "with_github_id": self.mapped_count(),
        }

        # Age ranges
        rows = self._conn.execute(f"""
            SELECT {AGE_RANGE_CASE} AS age_range, COUNT(*) AS cnt
            FROM employees e
            GROUP BY age_range
            ORDER BY age_range
        """).fetchall()
        result["age_ranges"] = {r["age_range"]: r["cnt"] for r in rows}

        # Job families
        rows = self._conn.execute("""
            SELECT job_family, COUNT(*) AS cnt FROM employees
            WHERE job_family IS NOT NULL AND job_family != ''
            GROUP BY job_family ORDER BY cnt DESC
        """).fetchall()
        result["job_families"] = {r["job_family"]: r["cnt"] for r in rows}

        # Top locations
        rows = self._conn.execute("""
            SELECT location, COUNT(*) AS cnt FROM employees
            WHERE location IS NOT NULL AND location != ''
            GROUP BY location ORDER BY cnt DESC LIMIT 10
        """).fetchall()
        result["locations_top10"] = {r["location"]: r["cnt"] for r in rows}

        # Sup Org Level 6
        rows = self._conn.execute("""
            SELECT sup_org_level_6, COUNT(*) AS cnt FROM employees
            WHERE sup_org_level_6 IS NOT NULL AND sup_org_level_6 != ''
            GROUP BY sup_org_level_6 ORDER BY cnt DESC
        """).fetchall()
        result["sup_org_level_6"] = {r["sup_org_level_6"]: r["cnt"] for r in rows}

        # Gender
        rows = self._conn.execute("""
            SELECT gender, COUNT(*) AS cnt FROM employees
            WHERE gender IS NOT NULL AND gender != ''
            GROUP BY gender
        """).fetchall()
        result["genders"] = {r["gender"]: r["cnt"] for r in rows}

        return result

    # ------------------------------------------------------------------
    # Queries — joined Copilot + org data
    # ------------------------------------------------------------------

    def analyze_copilot_by(
        self,
        group_by: str,
        metric: str = "active_users",
        filter_field: str | None = None,
        filter_value: str | None = None,
    ) -> dict[str, Any]:
        """Analyze Copilot usage grouped by an org dimension.

        Args:
            group_by: Column to group by (or 'age_range' for computed buckets).
            metric: Metric to aggregate.
            filter_field: Optional column to filter on.
            filter_value: Value for the filter.

        Returns:
            Dict with grouped results and metadata.
        """
        # Determine the GROUP BY expression
        if group_by == "age_range":
            group_expr = AGE_RANGE_CASE
        elif group_by.startswith("sup_org_level_") or group_by in (
            "gender", "location", "location_country", "job_family",
            "job_title", "job_level", "job_category", "management_level",
        ):
            group_expr = f"e.{group_by}"
        else:
            return {"error": f"Unsupported group_by field: {group_by}"}

        # Build WHERE clause
        where_clauses = ["e.github_id IS NOT NULL", "e.github_id != ''"]
        params: list[Any] = []
        if filter_field and filter_value:
            if filter_field == "age_range":
                where_clauses.append(f"{AGE_RANGE_CASE} = ?")
            else:
                where_clauses.append(f"e.{filter_field} LIKE ?")
                filter_value = f"%{filter_value}%"
            params.append(filter_value)

        where_sql = " AND ".join(where_clauses)

        # Build metric expression
        if metric == "active_users":
            select_metric = "COUNT(DISTINCT CASE WHEN (cu.completions_acceptances + cu.chat_turns + cu.agent_turns + cu.cli_turns) > 0 THEN cu.github_login END)"
        elif metric == "total_completions":
            select_metric = "COALESCE(SUM(cu.completions_acceptances), 0)"
        elif metric == "total_chat_turns":
            select_metric = "COALESCE(SUM(cu.chat_turns), 0)"
        elif metric == "total_lines_accepted":
            select_metric = "COALESCE(SUM(cu.completions_lines_accepted), 0)"
        elif metric == "total_activity":
            select_metric = "COALESCE(SUM(cu.completions_acceptances + cu.chat_turns + cu.agent_turns + cu.cli_turns), 0)"
        elif metric == "acceptance_rate":
            select_metric = """
                CASE WHEN SUM(cu.completions_suggestions) > 0
                     THEN ROUND(CAST(SUM(cu.completions_acceptances) AS REAL) / SUM(cu.completions_suggestions) * 100, 1)
                     ELSE 0.0
                END
            """
        else:
            select_metric = "COUNT(DISTINCT cu.github_login)"

        sql = f"""
            SELECT {group_expr} AS group_key, {select_metric} AS metric_value
            FROM employees e
            LEFT JOIN copilot_usage cu ON LOWER(e.github_id) = LOWER(cu.github_login)
            WHERE {where_sql}
            GROUP BY group_key
            HAVING group_key IS NOT NULL AND group_key != ''
            ORDER BY metric_value DESC
        """

        rows = self._conn.execute(sql, params).fetchall()
        groups = {r["group_key"]: r["metric_value"] for r in rows}

        # Metadata
        total_matched = self._conn.execute("""
            SELECT COUNT(DISTINCT cu.github_login) FROM copilot_usage cu
            JOIN employees e ON LOWER(e.github_id) = LOWER(cu.github_login)
            WHERE e.github_id IS NOT NULL AND e.github_id != ''
        """).fetchone()[0]

        total_usage = self._conn.execute(
            "SELECT COUNT(DISTINCT github_login) FROM copilot_usage"
        ).fetchone()[0]

        result = {
            "type": "org_copilot_analysis",
            "group_by": group_by,
            "metric": metric,
            "groups": groups,
            "total_copilot_users": total_usage,
            "matched_users": total_matched,
            "unmatched_users": total_usage - total_matched,
        }
        if filter_field and filter_value:
            result["filter"] = f"{filter_field} contains {filter_value}"

        return result

    def unmatched_github_users(self) -> list[str]:
        """Get GitHub logins from usage data that don't match any employee."""
        rows = self._conn.execute("""
            SELECT DISTINCT cu.github_login
            FROM copilot_usage cu
            LEFT JOIN employees e ON LOWER(e.github_id) = LOWER(cu.github_login)
            WHERE e.employee_id IS NULL
            ORDER BY cu.github_login
        """).fetchall()
        return [r["github_login"] for r in rows]

    def mapping_stats(self) -> dict[str, Any]:
        """Get statistics about GitHub ID mapping coverage."""
        total_employees = self.employee_count()
        mapped = self.mapped_count()
        total_usage = self._conn.execute(
            "SELECT COUNT(DISTINCT github_login) FROM copilot_usage"
        ).fetchone()[0]
        matched_usage = self._conn.execute("""
            SELECT COUNT(DISTINCT cu.github_login)
            FROM copilot_usage cu
            JOIN employees e ON LOWER(e.github_id) = LOWER(cu.github_login)
        """).fetchone()[0]

        # By method
        rows = self._conn.execute("""
            SELECT match_method, COUNT(*) AS cnt
            FROM github_id_mappings
            GROUP BY match_method
        """).fetchall()
        by_method = {r["match_method"]: r["cnt"] for r in rows}

        return {
            "total_employees": total_employees,
            "employees_with_github_id": mapped,
            "employees_without_github_id": total_employees - mapped,
            "total_copilot_users": total_usage,
            "matched_copilot_users": matched_usage,
            "unmatched_copilot_users": total_usage - matched_usage,
            "match_rate": round(matched_usage / max(total_usage, 1) * 100, 1),
            "mappings_by_method": by_method,
        }
