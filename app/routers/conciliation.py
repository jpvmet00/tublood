from datetime import date
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.db.models import Factura, Conciliacion, MovimientoBanco, Reclamo, Padron
from app.services.conciliation import facturas_vencidas

router = APIRouter(prefix="/conciliacion", tags=["conciliacion"])


@router.get("/vencidas")
def get_vencidas(
    mora_minima: int = Query(default=1, ge=0),
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
):
    """Return overdue invoices with saldo > 0, enriched with reclamo_activo flag."""
    facturas = facturas_vencidas(db, mora_minima=mora_minima)[:limit]
    hoy = date.today()

    try:
        clientes_con_reclamo = set(
            r.cliente_id
            for r in db.query(Reclamo.cliente_id).filter(Reclamo.activo == True).all()
        )
    except Exception:
        clientes_con_reclamo = set()

    result = []
    for f in facturas:
        dias_vencida = (hoy - f.fecha_vencimiento).days if f.fecha_vencimiento else None
        result.append({
            "id": f.id,
            "nro_factura": f.nro_factura,
            "cliente_id": f.cliente_id,
            "razon_social": f.razon_social,
            "cuit": f.cuit,
            "importe_original": f.importe_original,
            "saldo": f.saldo,
            "fecha_emision": str(f.fecha_emision) if f.fecha_emision else None,
            "fecha_vencimiento": str(f.fecha_vencimiento) if f.fecha_vencimiento else None,
            "condicion_venta": f.condicion_venta,
            "vendedor": f.vendedor,
            "estado": f.estado,
            "dias_vencida": dias_vencida,
            "reclamo_activo": f.cliente_id in clientes_con_reclamo,
        })
    return result


@router.get("/historial")
def get_historial(
    limit: int = Query(default=200, le=1000),
    db: Session = Depends(get_db),
):
    """Return conciliation records enriched with nro_factura and bank reference."""
    registros = (
        db.query(Conciliacion)
        .order_by(Conciliacion.fecha_conciliacion.desc())
        .limit(limit)
        .all()
    )

    result = []
    for c in registros:
        factura = db.query(Factura).filter(Factura.id == c.factura_id).first()
        mov = db.query(MovimientoBanco).filter(MovimientoBanco.id == c.movimiento_id).first() if c.movimiento_id else None

        result.append({
            "nro_factura": factura.nro_factura if factura else str(c.factura_id),
            "razon_social": factura.razon_social if factura else None,
            "banco": mov.banco if mov else None,
            "referencia": mov.referencia or (mov.concepto[:40] if mov and mov.concepto else None),
            "importe_aplicado": c.importe_aplicado,
            "estado": c.estado,
            "metodo": c.metodo,
            "fecha_conciliacion": str(c.fecha_conciliacion)[:10],
        })
    return result


@router.get("/resumen")
def get_resumen(db: Session = Depends(get_db)):
    """Return high-level stats."""
    total = db.query(Factura).count()
    con_saldo = db.query(Factura).filter(Factura.saldo > 0).count()
    cobradas = db.query(Factura).filter(Factura.estado == "cobrado").count()
    vencidas = len(facturas_vencidas(db))
    try:
        reclamos_abiertos = db.query(Reclamo).filter(Reclamo.activo == True).count()
    except Exception:
        reclamos_abiertos = 0

    from sqlalchemy import func
    saldo_total = db.query(func.sum(Factura.saldo)).scalar() or 0

    return {
        "total_facturas": total,
        "con_saldo_pendiente": con_saldo,
        "cobradas": cobradas,
        "vencidas": vencidas,
        "reclamos_abiertos": reclamos_abiertos,
        "saldo_total": round(saldo_total, 2),
    }


class MailCobroBody(BaseModel):
    cliente_id: str


@router.post("/mail-cobro")
def generar_mail_cobro(body: MailCobroBody, db: Session = Depends(get_db)):
    """Generate a deterministic payment request email for a client with overdue invoices."""
    hoy = date.today()

    facturas = (
        db.query(Factura)
        .filter(Factura.cliente_id == body.cliente_id, Factura.saldo > 0)
        .order_by(Factura.fecha_vencimiento.asc().nullsfirst())
        .all()
    )
    if not facturas:
        return {"error": "El cliente no tiene facturas pendientes."}

    padron = db.query(Padron).filter(Padron.cliente_id == body.cliente_id).first()
    razon = (padron.razon_social if padron else None) or body.cliente_id
    mail_to = (padron.mail_reclamo_factura if padron else None) or ""
    cuit = (padron.cuit if padron else None) or ""

    saldo_total = sum(f.saldo for f in facturas)
    vencidas = [f for f in facturas if f.fecha_vencimiento and f.fecha_vencimiento < hoy]

    detalle_lineas = []
    for f in facturas:
        dias = (hoy - f.fecha_vencimiento).days if f.fecha_vencimiento else 0
        venc_txt = f.fecha_vencimiento.strftime("%d/%m/%Y") if f.fecha_vencimiento else "sin fecha"
        estado_txt = f"VENCIDA hace {dias} dias" if dias > 0 else f"vence {venc_txt}"
        detalle_lineas.append(
            f"  - Factura {f.nro_factura} | Saldo: ${f.saldo:,.0f} | Vto: {venc_txt} | {estado_txt}"
        )
    detalle = "\n".join(detalle_lineas)

    asunto = f"Solicitud de regularizacion de deuda - {razon} - ${saldo_total:,.0f}"

    cuerpo = f"""Estimados,

Nos comunicamos desde TUBLOOD SA a fin de informarles que registramos facturas pendientes de pago a su nombre.

Cliente: {razon}
CUIT: {cuit}
Fecha: {hoy.strftime("%d/%m/%Y")}

Detalle de comprobantes pendientes:
{detalle}

Saldo total a regularizar: ${saldo_total:,.0f}

Les solicitamos que procedan con el pago a la brevedad posible. Para coordinar la forma de pago o en caso de consultas, pueden responder este mail o comunicarse con nuestra area de cobranzas.

En caso de haber realizado el pago recientemente, por favor ignoren este mensaje y enviennos el comprobante para su imputacion.

Quedamos a disposicion.

Saludos,
Area de Cobranzas
TUBLOOD SA"""

    return {
        "cliente_id": body.cliente_id,
        "razon_social": razon,
        "mail_to": mail_to,
        "asunto": asunto,
        "cuerpo": cuerpo,
        "saldo_total": saldo_total,
        "total_facturas": len(facturas),
        "facturas_vencidas": len(vencidas),
    }
