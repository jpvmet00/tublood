"""Core conciliation logic: bank movements vs. pending invoices."""
from datetime import date
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.adapters.factory import get_adapter
from app.db.models import Factura, MovimientoBanco, Conciliacion, Padron
from app.schemas.bank_movement import MovimientoCanonical
from app.config import settings


# ------------------------------------------------------------------
# Ingest bank file into movimientos_banco
# ------------------------------------------------------------------

def ingestar_movimientos(db: Session, filepath: Path, banco: Optional[str] = None) -> Dict[str, Any]:
    """Parse a bank file, persist new movements, and update padron.

    Returns dict with insertados, fecha_desde, fecha_hasta, ya_procesado.
    """
    from app.services.ingestion import construir_padron_desde_movimientos

    adapter = get_adapter(filepath, banco)
    movimientos = adapter.parse(filepath)

    fechas_parsed = [m.fecha for m in movimientos]
    fecha_desde = str(min(fechas_parsed)) if fechas_parsed else None
    fecha_hasta = str(max(fechas_parsed)) if fechas_parsed else None

    count = 0
    for mov in movimientos:
        existing = (
            db.query(MovimientoBanco)
            .filter(
                MovimientoBanco.banco == mov.banco,
                MovimientoBanco.fecha == mov.fecha,
                MovimientoBanco.concepto == mov.concepto,
                MovimientoBanco.importe == mov.importe,
            )
            .first()
        )
        if existing:
            continue

        db.add(
            MovimientoBanco(
                fecha=mov.fecha,
                concepto=mov.concepto,
                importe=mov.importe,
                cuit_extraido=mov.cuit_extraido,
                razon_social=mov.razon_social,
                banco=mov.banco,
                referencia=mov.referencia,
            )
        )
        count += 1

    db.commit()

    construir_padron_desde_movimientos(db)

    return {
        "insertados": count,
        "total_en_archivo": len(movimientos),
        "ya_procesado": count == 0 and len(movimientos) > 0,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
    }


# ------------------------------------------------------------------
# Conciliation
# ------------------------------------------------------------------

def conciliar_banco(db: Session, tolerance: Optional[float] = None) -> List[Dict[str, Any]]:
    # Ensure session is clean before starting
    try:
        db.rollback()
    except Exception:
        pass
    """Match unprocessed bank movements to pending invoices.

    Matching rules:
    - Movement CUIT -> Padron -> cliente_id -> Facturas with saldo > 0
    - Amount within +/- tolerance % of saldo (default 10%)
    - FIFO: oldest fecha_vencimiento first

    Returns a list of result dicts for the caller.
    """
    tol = tolerance if tolerance is not None else settings.tolerance_pct
    results = []

    movimientos = (
        db.query(MovimientoBanco)
        .filter(MovimientoBanco.procesado == False, MovimientoBanco.cuit_extraido.isnot(None))
        .order_by(MovimientoBanco.fecha)
        .all()
    )

    for mov in movimientos:
        padron = db.query(Padron).filter(Padron.cuit == mov.cuit_extraido).first()
        if not padron or not padron.cliente_id:
            continue

        facturas = (
            db.query(Factura)
            .filter(
                Factura.cliente_id == padron.cliente_id,
                Factura.saldo > 0,
            )
            .order_by(Factura.fecha_vencimiento.asc().nullsfirst())
            .all()
        )

        monto_restante = mov.importe
        for factura in facturas:
            if monto_restante <= 0:
                break

            limite_inf = factura.saldo * (1 - tol)
            limite_sup = factura.saldo * (1 + tol)

            if monto_restante < limite_inf:
                estado = "cobrado_parcial"
                aplicado = monto_restante
            elif monto_restante <= limite_sup:
                estado = "cobrado_total"
                aplicado = factura.saldo
            else:
                estado = "cobrado_total"
                aplicado = factura.saldo

            factura.saldo -= aplicado
            if factura.saldo < 0.01:
                factura.saldo = 0
                factura.estado = "cobrado"

            conciliacion = Conciliacion(
                factura_id=factura.id,
                movimiento_id=mov.id,
                importe_aplicado=round(aplicado, 2),
                estado=estado,
                metodo="home_banking",
            )
            db.add(conciliacion)
            monto_restante -= aplicado

            results.append({
                "movimiento_id": mov.id,
                "factura_id": factura.id,
                "nro_factura": factura.nro_factura,
                "cliente_id": factura.cliente_id,
                "cuit": mov.cuit_extraido,
                "importe_movimiento": mov.importe,
                "importe_aplicado": round(aplicado, 2),
                "estado": estado,
            })

        mov.procesado = True

    db.commit()
    return results


# ------------------------------------------------------------------
# Overdue report (for alert flow)
# ------------------------------------------------------------------

def facturas_vencidas(db: Session, mora_minima: Optional[int] = None) -> List[Factura]:
    mora = mora_minima if mora_minima is not None else settings.mora_minima
    hoy = date.today()
    return (
        db.query(Factura)
        .filter(
            Factura.saldo > 0,
            Factura.fecha_vencimiento < hoy,
        )
        .order_by(Factura.fecha_vencimiento.asc())
        .all()
    )
