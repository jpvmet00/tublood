from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.credit_risk import get_riesgo, get_riesgo_bulk

router = APIRouter(prefix="/riesgo", tags=["riesgo"])


@router.get("/{cuit}")
def consultar_riesgo(
    cuit: str,
    forzar: bool = Query(False, description="Ignorar cache y consultar BCRA en tiempo real"),
    db: Session = Depends(get_db),
):
    return get_riesgo(cuit, db, forzar=forzar)


@router.post("/bulk")
def consultar_riesgo_bulk(cuits: list[str], db: Session = Depends(get_db)):
    return get_riesgo_bulk(cuits, db)
