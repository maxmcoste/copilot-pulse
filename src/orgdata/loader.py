"""Load organizational structure data from Excel files."""

from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

import openpyxl

from .models import Employee

logger = logging.getLogger(__name__)

# Column index mapping (0-based) matching the Excel structure
_COL_MAP = {
    "company_ref_id": 0,
    "company": 1,
    "location_country": 2,
    "supervisory_org": 3,
    "supervisory_org_id": 4,
    "employee_id": 5,
    "position_title": 8,
    "matricola": 10,
    "worker_type": 11,
    "name": 12,
    "surname": 13,
    "email": 14,
    "github_id": 15,
    "location": 16,
    "location_id": 17,
    "cdc_code": 18,
    "cost_center_id": 19,
    "is_manager": 20,
    "hr_business_partner": 21,
    "hr_director": 22,
    "business_title": 24,
    "job_profile": 25,
    "job_family": 26,
    "employee_type": 27,
    "contract_type": 28,
    "management_level": 29,
    "time_type": 30,
    "fte": 31,
    "original_hire_date": 32,
    "continuous_service_date": 33,
    "length_of_service": 34,
    "company_service_date": 35,
    "age_col1": 36,
    "time_in_position": 37,
    "email_work": 39,
    "job_code": 40,
    "job_title": 41,
    "job_level": 42,
    "job_category": 43,
    "gender": 53,
    "date_of_birth": 54,
    "age_col2": 55,
    "top_level_sup_org": 61,
    "sup_org_level_2": 62,
    "sup_org_level_3": 63,
    "sup_org_level_4": 64,
    "sup_org_level_5": 65,
    "sup_org_level_6": 66,
    "sup_org_level_7": 67,
    "sup_org_level_8": 68,
    "sup_org_level_9": 69,
    "sup_org_level_10": 70,
}


def _safe_str(val: Any) -> str:
    """Convert a cell value to string, handling None."""
    if val is None:
        return ""
    return str(val).strip()


def _safe_date(val: Any) -> date | None:
    """Convert a cell value to date."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    return None


def _safe_int(val: Any) -> int | None:
    """Convert a cell value to int."""
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _safe_float(val: Any) -> float:
    """Convert a cell value to float."""
    if val is None:
        return 1.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 1.0


class OrgDataLoader:
    """Load employee org structure from an Excel file.

    Args:
        file_path: Path to the Excel (.xlsx) file.
    """

    def __init__(self, file_path: str | Path) -> None:
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"Org structure file not found: {self.file_path}")

    def load(self) -> list[Employee]:
        """Load all employee records from the Excel file.

        Returns:
            List of Employee model instances.
        """
        wb = openpyxl.load_workbook(str(self.file_path), read_only=True, data_only=True)
        ws = wb["Data"]

        employees: list[Employee] = []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0:
                continue  # skip header

            # Skip completely empty rows
            if not any(row[:20]):
                continue

            github_id_val = _safe_str(row[_COL_MAP["github_id"]]) or None
            is_manager_raw = _safe_str(row[_COL_MAP["is_manager"]])
            is_manager = True if is_manager_raw.lower() in ("yes", "true", "1", "y") else (
                False if is_manager_raw else None
            )

            # Age: prefer column 55 (second Age), fall back to column 36
            age = _safe_int(row[_COL_MAP["age_col2"]]) or _safe_int(row[_COL_MAP["age_col1"]])

            emp = Employee(
                employee_id=_safe_str(row[_COL_MAP["employee_id"]]),
                matricola=_safe_str(row[_COL_MAP["matricola"]]),
                github_id=github_id_val,
                name=_safe_str(row[_COL_MAP["name"]]),
                surname=_safe_str(row[_COL_MAP["surname"]]),
                email=_safe_str(row[_COL_MAP["email"]]) or None,
                email_work=_safe_str(row[_COL_MAP["email_work"]]) or None,
                gender=_safe_str(row[_COL_MAP["gender"]]) or None,
                age=age,
                date_of_birth=_safe_date(row[_COL_MAP["date_of_birth"]]),
                company=_safe_str(row[_COL_MAP["company"]]),
                company_ref_id=_safe_str(row[_COL_MAP["company_ref_id"]]),
                location_country=_safe_str(row[_COL_MAP["location_country"]]),
                location=_safe_str(row[_COL_MAP["location"]]),
                location_id=_safe_str(row[_COL_MAP["location_id"]]),
                position_title=_safe_str(row[_COL_MAP["position_title"]]),
                business_title=_safe_str(row[_COL_MAP["business_title"]]),
                job_profile=_safe_str(row[_COL_MAP["job_profile"]]),
                job_family=_safe_str(row[_COL_MAP["job_family"]]),
                job_code=_safe_str(row[_COL_MAP["job_code"]]),
                job_title=_safe_str(row[_COL_MAP["job_title"]]),
                job_level=_safe_str(row[_COL_MAP["job_level"]]),
                job_category=_safe_str(row[_COL_MAP["job_category"]]),
                management_level=_safe_str(row[_COL_MAP["management_level"]]),
                worker_type=_safe_str(row[_COL_MAP["worker_type"]]),
                employee_type=_safe_str(row[_COL_MAP["employee_type"]]),
                contract_type=_safe_str(row[_COL_MAP["contract_type"]]),
                time_type=_safe_str(row[_COL_MAP["time_type"]]),
                fte=_safe_float(row[_COL_MAP["fte"]]),
                is_manager=is_manager,
                original_hire_date=_safe_date(row[_COL_MAP["original_hire_date"]]),
                continuous_service_date=_safe_date(row[_COL_MAP["continuous_service_date"]]),
                company_service_date=_safe_date(row[_COL_MAP["company_service_date"]]),
                length_of_service=_safe_str(row[_COL_MAP["length_of_service"]]),
                time_in_position=_safe_str(row[_COL_MAP["time_in_position"]]),
                cdc_code=_safe_str(row[_COL_MAP["cdc_code"]]),
                cost_center_id=_safe_str(row[_COL_MAP["cost_center_id"]]),
                supervisory_org=_safe_str(row[_COL_MAP["supervisory_org"]]),
                supervisory_org_id=_safe_str(row[_COL_MAP["supervisory_org_id"]]),
                top_level_sup_org=_safe_str(row[_COL_MAP["top_level_sup_org"]]),
                sup_org_level_2=_safe_str(row[_COL_MAP["sup_org_level_2"]]),
                sup_org_level_3=_safe_str(row[_COL_MAP["sup_org_level_3"]]),
                sup_org_level_4=_safe_str(row[_COL_MAP["sup_org_level_4"]]),
                sup_org_level_5=_safe_str(row[_COL_MAP["sup_org_level_5"]]),
                sup_org_level_6=_safe_str(row[_COL_MAP["sup_org_level_6"]]),
                sup_org_level_7=_safe_str(row[_COL_MAP["sup_org_level_7"]]),
                sup_org_level_8=_safe_str(row[_COL_MAP["sup_org_level_8"]]),
                sup_org_level_9=_safe_str(row[_COL_MAP["sup_org_level_9"]]),
                sup_org_level_10=_safe_str(row[_COL_MAP["sup_org_level_10"]]),
                hr_business_partner=_safe_str(row[_COL_MAP["hr_business_partner"]]),
                hr_director=_safe_str(row[_COL_MAP["hr_director"]]),
            )
            employees.append(emp)

        wb.close()
        logger.info("Loaded %d employees from %s", len(employees), self.file_path.name)
        return employees
