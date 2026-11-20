import os
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import workflows, maira, portals
from .gemini_deploy_probe import run_gemini_deploy_probe

app = FastAPI(title="Smart Contract API", version="0.1.0")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True,
                   allow_methods=["GET", "POST", "PUT", "PATCH"], allow_headers=["Authorization", "Content-Type"])

@app.get("/health")
def health():
    return {"status": "ok", "product": "smart-contract", "version": "0.1.0"}

app.include_router(workflows.router)
app.include_router(maira.router)
app.include_router(portals.router)


# Bounded, read-only, credentialed production-path diagnostic, only in the
# existing Smart Contract Development environment. Once per new API process,
# with no document upload, new service, API-key echo or user action.
@app.on_event("startup")
async def development_gemini_boot_probe():
    if os.getenv("RAILWAY_ENVIRONMENT_ID") != "6e8d45ca-d6f2-448c-a48a-63e5a2ab1806":
        return
    api_key = os.getenv("SMART_GEMINI_API_KEY", "").strip()
    if not api_key:
        return
    asyncio.create_task(run_gemini_deploy_probe(api_key))
