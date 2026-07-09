import logging
from typing import Optional
import httpx
from sqlalchemy.orm import Session
from src.config.settings import settings
from src.config.config_service import ConfigService

logger = logging.getLogger(__name__)

SENDFOX_BASE_URL = "https://api.sendfox.com"


class SendFoxService:
    """Adds contacts to SendFox lists on signup. Never raises — signup flow must not break."""

    def __init__(self, db: Session):
        self.db = db

        self.token = ConfigService.get_value(
            "sendfox_api_token", settings.SENDFOX_API_TOKEN, db=db
        )

        self.list_ids = {
            "student": ConfigService.get_value(
                "sendfox_student_list_id", settings.SENDFOX_STUDENT_LIST_ID, db=db
            ),
            "guardian": ConfigService.get_value(
                "sendfox_guardian_list_id", settings.SENDFOX_GUARDIAN_LIST_ID, db=db
            ),
            "institution_admin": ConfigService.get_value(
                "sendfox_institution_list_id",
                settings.SENDFOX_INSTITUTION_LIST_ID,
                db=db,
            ),
        }

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def add_contact(
        self,
        email: str,
        user_type: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ):
        list_id = self.list_ids.get(user_type)
        if not list_id or not self.token:
            logger.warning("SendFox not configured for user_type=%s", user_type)
            return

        try:
            list_id = int(list_id)
        except (TypeError, ValueError):
            logger.error(
                "SendFox list_id for %s is not a valid int: %r", user_type, list_id
            )
            return

        payload = {
            "email": email,
            "first_name": first_name or "",
            "last_name": last_name or "",
            "lists": [list_id],
        }

        try:
            async with httpx.AsyncClient(
                base_url=SENDFOX_BASE_URL, timeout=10
            ) as client:
                resp = await client.post(
                    "/contacts", json=payload, headers=self._headers()
                )

                if resp.status_code == 200:
                    return resp.json()

                if resp.status_code == 400:
                    # Likely already exists — find contact_id then attach to list
                    await self._attach_existing_contact(client, email, list_id)
                    return

                logger.error(
                    "SendFox create_contact failed [%s]: %s",
                    resp.status_code,
                    resp.text,
                )
        except httpx.HTTPError as exc:
            logger.error("SendFox request error for %s: %s", email, exc)

    async def _attach_existing_contact(
        self, client: httpx.AsyncClient, email: str, list_id: int
    ):
        try:
            resp = await client.get(
                "/contacts", params={"email": email}, headers=self._headers()
            )
            if resp.status_code != 200:
                logger.error("SendFox lookup failed for %s: %s", email, resp.text)
                return

            data = resp.json().get("data", [])
            if not data:
                logger.warning(
                    "SendFox: contact %s not found after 400 on create", email
                )
                return

            contact_id = data[0]["id"]
            attach_resp = await client.post(
                f"/lists/{list_id}/contacts",
                json={"contact_id": contact_id},
                headers=self._headers(),
            )
            if attach_resp.status_code != 200:
                logger.error(
                    "SendFox attach failed for %s: %s", email, attach_resp.text
                )
        except httpx.HTTPError as exc:
            logger.error("SendFox attach error for %s: %s", email, exc)
