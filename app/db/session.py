from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.db.models import Base
    Base.metadata.create_all(bind=engine)
    _migrate()


def _migrate() -> None:
    """Add new columns to existing tables without dropping data."""
    new_columns = [
        ("facturas",          "razon_social",          "VARCHAR(300)"),
        ("movimientos_banco", "razon_social",          "VARCHAR(300)"),
        ("padron",            "mail_reclamo_factura",  "VARCHAR(200)"),
        ("padron",            "mail_atencion_cliente", "VARCHAR(200)"),
        ("reclamos",          "cuit",                  "VARCHAR(20)"),
        ("reclamos",          "descripcion",           "TEXT"),
        ("reclamos",          "ultima_respuesta",      "TEXT"),
        ("reclamos",          "historico_respuestas",  "TEXT"),
        ("reclamos",          "como_se_resolvio",      "TEXT"),
        ("reclamos",          "activo",                "BOOLEAN DEFAULT 1"),
        ("reclamos",          "fecha_inicio",          "DATE"),
        ("reclamos",          "fecha_cierre",          "DATE"),
        ("reclamos",          "factura_id_nullable",   "INTEGER"),  # handled via model nullable
    ]
    with engine.connect() as conn:
        for table, col, col_type in new_columns:
            if col == "factura_id_nullable":
                continue
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                conn.commit()
            except Exception:
                pass  # column already exists
