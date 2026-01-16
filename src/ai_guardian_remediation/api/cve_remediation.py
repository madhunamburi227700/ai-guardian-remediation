from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from fastapi.exceptions import HTTPException
from typing import Annotated, Optional, Literal

from ai_guardian_remediation.services.cve_remediation import (
    CVERemediationService,
)

from pydantic import BaseModel, field_validator
from enum import Enum
import logging


class FixRequest(BaseModel):
    id: Optional[str] = None
    vulnerability_id: Optional[str] = None
    session_id: Optional[str] = None
    token: str
    platform: str
    organization: str
    repository: str
    cve_id: str
    package: str
    branch: Optional[str] = None
    message_type: Literal["start_generate", "start_apply", "followup"]
    user_message: Optional[str] = None
    user_email: Optional[str] = None

    @field_validator("session_id")
    def empty_string_to_none(cls, v):
        if v == "":
            return None
        return v


class ModeFix(str, Enum):
    generate = "generate"
    apply = "apply"


router = APIRouter(prefix="/cve-remediation", tags=["cve-remediation"])


@router.post("/v1/fix")
async def fix(
    input: FixRequest,
    mode: Annotated[ModeFix, Query()],
):
    logging.info(
        "Received request to remediate CVE %s in package %s in repo at %s using mode %s",
        input.cve_id,
        input.package,
        input.repository,
        input.message_type,
    )

    try:
        remediation_service = CVERemediationService(
            cve_id=input.cve_id,
            package=input.package,
            git_token=input.token,
            platform=input.platform,
            organization=input.organization,
            repository=input.repository,
            branch=input.branch,
            vulnerability_id=input.vulnerability_id,
            remediation_id=input.id,
            user_email=input.user_email,
        )

        match mode:
            case ModeFix.generate:
                return StreamingResponse(
                    remediation_service.generate_fix(
                        input.session_id,
                        input.message_type,
                        input.user_message,
                    ),
                    media_type="text/event-stream",
                )

            case ModeFix.apply:
                return StreamingResponse(
                    remediation_service.apply_fix(),
                    media_type="text/event-stream",
                )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
