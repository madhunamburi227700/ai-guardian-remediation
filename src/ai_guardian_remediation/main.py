from fastapi import FastAPI

from fastapi.responses import JSONResponse

app = FastAPI()

# Include your routers here
from src.ai_guardian_remediation.api import cve_remediation

app.include_router(cve_remediation.router)


@app.get("/healthz")
async def healthz():
    """Health check endpoint."""
    return JSONResponse(
        content={"status": "ok", "message": "Service is up and running"}
    )
