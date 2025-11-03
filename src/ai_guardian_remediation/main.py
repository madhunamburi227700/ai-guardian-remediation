from fastapi import FastAPI

from fastapi.responses import JSONResponse
import logging
from ai_guardian_remediation.common.scheduler.core import schedule_tasks
from ai_guardian_remediation.api import cve_remediation, sast_remediation
from contextlib import asynccontextmanager
# from ai_guardian_remediation.storage.db import db


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # await db.migrate_tables()
    scheduler = schedule_tasks()
    yield
    scheduler.stop()


app = FastAPI(lifespan=lifespan)

app.include_router(cve_remediation.router)
app.include_router(sast_remediation.router)


@app.get("/healthz")
async def healthz():
    """Health check endpoint."""
    return JSONResponse(
        content={"status": "ok", "message": "Service is up and running"}
    )
