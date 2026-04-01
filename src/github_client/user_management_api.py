"""Copilot seat and billing management API."""

from __future__ import annotations

import logging

from .base_client import GitHubBaseClient
from .models import SeatAssignment, SeatInfo

logger = logging.getLogger(__name__)


class UserManagementAPI:
    """Client for Copilot billing and seat management endpoints.

    Args:
        client: Configured GitHubBaseClient instance.
    """

    def __init__(self, client: GitHubBaseClient) -> None:
        self._client = client

    async def get_billing(self, org: str) -> SeatInfo:
        """Fetch Copilot billing info including seat breakdown.

        Args:
            org: Organization name.

        Returns:
            SeatInfo with seat counts and breakdown.
        """
        resp = await self._client.get(f"/orgs/{org}/copilot/billing")
        data = resp.json()

        return SeatInfo(
            seat_breakdown=data.get("seat_breakdown", {}),
            total_seats=data.get("total_seats", 0),
        )

    async def get_seats(self, org: str) -> SeatInfo:
        """Fetch detailed seat assignments with per-user activity.

        Args:
            org: Organization name.

        Returns:
            SeatInfo with individual seat details.
        """
        all_seats: list[SeatAssignment] = []
        page = 1
        per_page = 100
        total_seats = 0

        while True:
            resp = await self._client.get(
                f"/orgs/{org}/copilot/billing/seats",
                params={"page": str(page), "per_page": str(per_page)},
            )
            data = resp.json()
            total_seats = data.get("total_seats", total_seats)

            for seat in data.get("seats", []):
                assignee = seat.get("assignee", {})
                all_seats.append(
                    SeatAssignment(
                        login=assignee.get("login", ""),
                        assigned_at=seat.get("created_at"),
                        last_activity_at=seat.get("last_activity_at"),
                        last_activity_editor=seat.get("last_activity_editor"),
                        plan_type=seat.get("plan_type", ""),
                        pending_cancellation_date=seat.get("pending_cancellation_date"),
                    )
                )

            if len(data.get("seats", [])) < per_page:
                break
            page += 1

        logger.info("Fetched %d seat assignments for org %s", len(all_seats), org)
        return SeatInfo(total_seats=total_seats, seats=all_seats)

    async def get_user_copilot_status(self, org: str, username: str) -> dict:
        """Check Copilot status for a specific user.

        Args:
            org: Organization name.
            username: GitHub username.

        Returns:
            Dict with user's Copilot seat status.
        """
        resp = await self._client.get(f"/orgs/{org}/members/{username}/copilot")
        return resp.json()
