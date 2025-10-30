from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session

from ai_guardian_remediation.storage.db.remediation import SQLRemediation, Status


class DatabaseManager:
    def __init__(self, db_session: Session):
        self.remediation = SQLRemediation(db_session)

    async def _update_remediation(
        self,
        remediation_id: str,
        status: Status,
        extra_fields: dict,
    ):
        update_data = {**extra_fields}
        if status:
            update_data["status"] = status

        if status == Status.COMPLETED:
            update_data["completed_at"] = datetime.now(timezone.utc)

        self.remediation.update_remediation(
            remediation_id=remediation_id,
            update_data=update_data,
        )

    async def save_remediation(
        self,
        remediation_id: str,
        vulnerability_id: str,
        status: Status,
        extra_fields: dict = None,
    ):
        if extra_fields is None:
            extra_fields = {}

        # If remediation id  is provided, proceed using the id
        if remediation_id:
            if status == Status.STARTED:
                self.remediation.create_remediation(
                    id=remediation_id, vulnerability_id=vulnerability_id
                )
            else:
                if not self.remediation.get_remediation_by_id(remediation_id):
                    logging.error(f"Remediation with id {remediation_id} not found.")
                    return

                await self._update_remediation(remediation_id, status, extra_fields)
        else:
            # Proceed using vulnerability id
            db_data = self.remediation.get_remediations_by_vulnerability_id(
                vulnerability_id
            )
            if not len(db_data) and status == Status.STARTED:
                # Create new remediation
                self.remediation.create_remediation(
                    id=None, vulnerability_id=vulnerability_id
                )
            else:
                # Update existing remediation
                if not len(db_data):
                    logging.error(
                        f"Remediation with vulnerability id {vulnerability_id} not found."
                    )
                    return
                await self._update_remediation(db_data[0]["id"], status, extra_fields)
