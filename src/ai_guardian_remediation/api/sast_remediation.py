from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from fastapi.exceptions import HTTPException
from typing import Annotated, Optional, Literal

from ai_guardian_remediation.services.sast_remediation import (
    SASTRemediationService,
)
from pydantic import BaseModel, field_validator
from enum import Enum
import logging


class ModeFix(str, Enum):
    generate = "generate"
    apply = "apply"
    # reject = "reject"


class SASTFixRequest(BaseModel):
    id: Optional[str] = None
    vulnerability_id: Optional[str] = None
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
    input: SASTFixRequest, mode: Annotated[ModeFix, Query()]
):
    logging.info(
        "Received request to remediate a SAST finding %s in repo %s",
        input.rule,
        input.repository,
    )

    try:
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

        match mode:
            case ModeFix.generate:
                return StreamingResponse(
                    service.generate_fix(
                        session_id=input.session_id,
                        message_type=input.message_type,
                        user_message=input.user_message,
                    ),
                    media_type="text/event-stream",
                )
            case ModeFix.apply:
                return StreamingResponse(
                    service.process_approval(), media_type="text/event-stream"
                )
            # case ModeFix.reject:
            #     return StreamingResponse(service.cleanup(), media_type="text/event-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
