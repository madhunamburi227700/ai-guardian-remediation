from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from typing import Annotated, Optional, Literal

from ai_guardian_remediation.services.sast_remediation import (
    SASTRemediationService,
)
from pydantic import BaseModel, field_validator
from enum import Enum
import logging


class ActionEnum(str, Enum):
    generate = "generate"
    approve = "approve"
    reject = "reject"


class SASTFixRequest(BaseModel):
    id: Optional[str] = None
    vulnerability_id: str
    session_id: Optional[str] = None
    token: str
    platform: str
    organization: str
    repository: str
    branch: str
    rule: str
    rule_message: str
    file_path: str
    line_no: int
    message_type: Literal["start_generate", "start_apply", "followup"]
    user_message: Optional[str] = None
    user_email: Optional[str] = None

    @field_validator("session_id")
    def empty_string_to_none(cls, v):
        if v == "":
            return None
        return v


router = APIRouter(prefix="/sast-remediation", tags=["sast-remediation"])


@router.post("/v1/fix")
async def fix_sast_remediation(
    input: SASTFixRequest, action: Annotated[ActionEnum, Query()]
):
    logging.info(
        "Received request to remediate a SAST finding %s in repo %s",
        input.rule,
        input.repository,
    )

    service = SASTRemediationService(
        platform=input.platform,
        organization=input.organization,
        repository=input.repository,
        branch=input.branch,
        rule=input.rule,
        rule_message=input.rule_message,
        file_path=input.file_path,
        line_no=input.line_no,
        git_token=input.token,
        vulnerability_id=input.vulnerability_id,
        remediation_id=input.id,
        user_email=input.user_email,
    )

    match action:
        case ActionEnum.generate:
            return StreamingResponse(
                service.generate_fix(
                    session_id=input.session_id,
                    message_type=input.message_type,
                    user_message=input.user_message,
                ),
                media_type="text/event-stream",
            )
        case ActionEnum.approve:
            return StreamingResponse(
                service.process_approval(), media_type="text/event-stream"
            )
        case ActionEnum.reject:
            return StreamingResponse(service.cleanup(), media_type="text/event-stream")
