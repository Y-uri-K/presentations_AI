from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.logging_setup import setup_logging
from app.database import SessionLocal
from app.routers import agents, auth, presentations, templates
from app.services.auth_service import ensure_user_profile_columns
from app.services.template_service import ensure_template_catalog_schema

setup_logging()
settings = get_settings()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(agents.router)
app.include_router(templates.router)
app.include_router(presentations.router)


@app.on_event("startup")
def run_startup_migrations():
    db = SessionLocal()
    try:
        ensure_user_profile_columns(db)
        ensure_template_catalog_schema(db)
    finally:
        db.close()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {"message": "Hello World"}
