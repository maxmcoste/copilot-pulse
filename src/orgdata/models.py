"""Pydantic models for organizational employee data."""

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class Employee(BaseModel):
    """An employee record from the organizational structure spreadsheet."""

    # Identifiers
    employee_id: str = ""
    matricola: str = ""
    github_id: Optional[str] = None

    # Personal (non-sensitive subset)
    name: str = ""
    surname: str = ""
    email: Optional[str] = None
    email_work: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    date_of_birth: Optional[date] = None

    # Company
    company: str = ""
    company_ref_id: str = ""
    location_country: str = ""
    location: str = ""
    location_id: str = ""

    # Job
    position_title: str = ""
    business_title: str = ""
    job_profile: str = ""
    job_family: str = ""
    job_code: str = ""
    job_title: str = ""
    job_level: str = ""
    job_category: str = ""
    management_level: str = ""
    worker_type: str = ""
    employee_type: str = ""
    contract_type: str = ""
    time_type: str = ""
    fte: float = 1.0
    is_manager: Optional[bool] = None

    # Dates & tenure
    original_hire_date: Optional[date] = None
    continuous_service_date: Optional[date] = None
    company_service_date: Optional[date] = None
    length_of_service: str = ""
    time_in_position: str = ""

    # Cost center
    cdc_code: str = ""
    cost_center_id: str = ""

    # Supervisory Organization hierarchy
    supervisory_org: str = ""
    supervisory_org_id: str = ""
    top_level_sup_org: str = ""
    sup_org_level_2: str = ""
    sup_org_level_3: str = ""
    sup_org_level_4: str = ""
    sup_org_level_5: str = ""
    sup_org_level_6: str = ""
    sup_org_level_7: str = ""
    sup_org_level_8: str = ""
    sup_org_level_9: str = ""
    sup_org_level_10: str = ""

    # HR
    hr_business_partner: str = ""
    hr_director: str = ""

    @property
    def full_name(self) -> str:
        return f"{self.name} {self.surname}".strip()

    @property
    def age_range(self) -> str:
        """Bucket age into standard ranges."""
        if self.age is None:
            return "Unknown"
        if self.age < 25:
            return "<25"
        elif self.age < 30:
            return "25-29"
        elif self.age < 35:
            return "30-34"
        elif self.age < 40:
            return "35-39"
        elif self.age < 45:
            return "40-44"
        elif self.age < 50:
            return "45-49"
        elif self.age < 55:
            return "50-54"
        elif self.age < 60:
            return "55-59"
        else:
            return "60+"

    def get_sup_org_level(self, level: int) -> str:
        """Get supervisory org at a specific level (2-10)."""
        return getattr(self, f"sup_org_level_{level}", "")

    def org_path(self) -> list[str]:
        """Return the full org hierarchy as a list from top to deepest."""
        path = []
        for lvl in [
            self.top_level_sup_org,
            self.sup_org_level_2,
            self.sup_org_level_3,
            self.sup_org_level_4,
            self.sup_org_level_5,
            self.sup_org_level_6,
            self.sup_org_level_7,
            self.sup_org_level_8,
            self.sup_org_level_9,
            self.sup_org_level_10,
        ]:
            if lvl:
                path.append(lvl)
            else:
                break
        return path
