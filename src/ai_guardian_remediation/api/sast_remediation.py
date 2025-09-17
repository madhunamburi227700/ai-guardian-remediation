from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Annotated
import os

from ai_guardian_remediation.services.sast_remediation_service import (
    SASTRemediationService,
)
from pydantic import BaseModel
from enum import Enum


class ActionEnum(str, Enum):
    generate = "generate"
    approve = "approve"
    reject = "reject"


class SASTFixRequest(BaseModel):
    platform: str
    organization: str
    repository: str
    branch: str
    rule: str
    rule_message: str
    file_path: str
    line_no: int


router = APIRouter(prefix="/sast-remediation", tags=["sast-remediation"])


@router.post("/v1/fix")
async def fix_sast_remediation(
    input: SASTFixRequest, action: Annotated[ActionEnum, Query()]
):
    git_token = os.getenv("GH_TOKEN")
    service = SASTRemediationService(
        platform=input.platform,
        organization=input.organization,
        repository=input.repository,
        branch=input.branch,
        rule=input.rule,
        rule_message=input.rule_message,
        file_path=input.file_path,
        line_no=input.line_no,
        git_token=git_token,
    )

    match action:
        case ActionEnum.generate:
            return StreamingResponse(
                service.generate_fix(), media_type="text/event-stream"
            )
        case ActionEnum.approve:
            return StreamingResponse(
                service.process_approval(), media_type="text/event-stream"
            )
        case ActionEnum.reject:
            service.cleanup()
            return JSONResponse({"status": "ok", "message": "Repository cleaned up"})
