from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from typing import Annotated
import os

from ai_guardian_remediation.services.cve_remediation_service import (
    CVERemediationService,
)

from pydantic import BaseModel, field_validator
from enum import Enum
from typing import Optional, Literal
import logging


class FixRequest(BaseModel):
    session_id: Optional[str] = None
    remote_url: str
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
        input.remote_url,
        input.message_type,
    )

    # TODO: We will get this from the DB
    token = os.getenv("GH_TOKEN")
    # token = os.environ["GH_TOKEN"]

    remediation_service = CVERemediationService(
        cve_id=input.cve_id,
        package=input.package,
        git_token=token,
        remote_url=input.remote_url,
        branch=input.branch,
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
            logging.info("Apply fix")
            return StreamingResponse(
                remediation_service.apply_fix(
                    input.session_id,
                    input.message_type,
                    input.user_message,
                ),
                media_type="text/event-stream",
            )
