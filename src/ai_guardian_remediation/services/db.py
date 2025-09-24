from ai_guardian_remediation.storage.db import remediation
from datetime import datetime, timezone
import uuid


async def save_remediation(
    db_session, scan_result_id, status: str, extra_fields: dict = None
):
    if extra_fields is None:
        extra_fields = {}

    db_data = remediation.get_remediations_by_scan_result_id(db_session, scan_result_id)
    if not len(db_data):
        remediation_data = {
            "id": str(uuid.uuid4()),
            "scan_result_id": extra_fields.get("scan_result_id", None),
            "status": status,
            "started_at": datetime.now(timezone.utc),
            "completed_at": None,
        }
        remediation.insert_remediation(db_session, remediation_data)
    else:
        # Update existing remediation
        update_data = {"status": status, **extra_fields}
        if status == "completed":
            update_data["completed_at"] = datetime.now(timezone.utc)

        remediation.update_remediation(
            db_session,
            remediation_id=db_data[0].id,
            update_data=update_data,
        )
