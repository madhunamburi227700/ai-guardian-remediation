from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Annotated

from ai_guardian_remediation.services.sast_remediation import (
    SASTRemediationService,
)
from pydantic import BaseModel
from enum import Enum


class ActionEnum(str, Enum):
    generate = "generate"
    approve = "approve"
    reject = "reject"


class SASTFixRequest(BaseModel):
    scan_result_id: str
    repository_url: str
    token: str
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
    service = SASTRemediationService(
        repository_url=input.repository_url,
        branch=input.branch,
        rule=input.rule,
        rule_message=input.rule_message,
        file_path=input.file_path,
        line_no=input.line_no,
        git_token=input.token,
        scan_result_id=input.scan_result_id,
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
