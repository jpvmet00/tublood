from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.session import init_db
from app.routers import upload, conciliation, reclamos, admin
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    yield


app = FastAPI(
    title="TUBLOOD - Sistema de Conciliacion",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(upload.router)
app.include_router(conciliation.router)
app.include_router(reclamos.router)
app.include_router(admin.router)


@app.get("/health")
def health():
    return {"status": "ok"}
