from fastapi import FastAPI

from fastapi.responses import JSONResponse

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

app = FastAPI()

# Include your routers here
from src.ai_guardian_remediation.api import cve_remediation
from src.ai_guardian_remediation.api import sast_remediation

app.include_router(cve_remediation.router)
app.include_router(sast_remediation.router)


@app.get("/healthz")
async def healthz():
    """Health check endpoint."""
    return JSONResponse(
        content={"status": "ok", "message": "Service is up and running"}
    )
