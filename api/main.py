from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import servers, flavors, storage, databases, tasks

app = FastAPI(
    title="proxlab API",
    description="VM orchestration API for Proxmox + TrueNAS + Postgres (OpenStack Nova-style)",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(servers.router)
app.include_router(flavors.router)
app.include_router(storage.router)
app.include_router(databases.router)
app.include_router(tasks.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "proxlab-api"}
