from fastapi import FastAPI

from fastapi.responses import JSONResponse

app = FastAPI()

# Include your routers here
# app.include_router()


@app.get("/healthz")
async def healthz():
    """Health check endpoint."""
    return JSONResponse(
        content={"status": "ok", "message": "Service is up and running"}
    )
