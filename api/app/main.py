import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import workflows, maira

app = FastAPI(title="Smart Contract API", version="0.1.0")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True,
                   allow_methods=["GET", "POST", "PUT", "PATCH"], allow_headers=["Authorization", "Content-Type"])

@app.get("/health")
def health():
    return {"status": "ok", "product": "smart-contract", "version": "0.1.0"}

app.include_router(workflows.router)
app.include_router(maira.router)
