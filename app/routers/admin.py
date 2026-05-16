import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from app.config import settings
from app.db.session import engine, init_db

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/reset-db")
def reset_db():
    """Drop and recreate the database. Deletes all data."""
    try:
        # Close all connections
        engine.dispose()

        # Delete the file if it's SQLite
        if "sqlite" in settings.database_url:
            db_path = settings.database_url.replace("sqlite:///", "").replace("sqlite://", "")
            db_path = Path(db_path)
            if db_path.exists():
                os.remove(db_path)

        # Recreate schema
        init_db()
        return {"ok": True, "mensaje": "Base de datos reiniciada correctamente."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
