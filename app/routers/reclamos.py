from datetime import date, datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Reclamo

router = APIRouter(prefix="/reclamos", tags=["reclamos"])

SEP = "|||"


class ResponderBody(BaseModel):
    texto: str


@router.get("")
def list_reclamos(
    solo_activos: bool = False,
    cliente_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Reclamo)
    if solo_activos:
        q = q.filter(Reclamo.activo == True)
    if cliente_id:
        q = q.filter(Reclamo.cliente_id == cliente_id)
    reclamos = q.order_by(Reclamo.fecha_inicio.desc()).all()
    return [_serializar(r) for r in reclamos]


@router.get("/{reclamo_id}")
def get_reclamo(reclamo_id: int, db: Session = Depends(get_db)):
    r = db.query(Reclamo).filter(Reclamo.id == reclamo_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Reclamo no encontrado")
    return _serializar(r)


@router.post("/{reclamo_id}/responder")
def responder(reclamo_id: int, body: ResponderBody, db: Session = Depends(get_db)):
    r = db.query(Reclamo).filter(Reclamo.id == reclamo_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Reclamo no encontrado")

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    entrada = f"{ts}|{body.texto.strip()}"

    if r.historico_respuestas:
        r.historico_respuestas = r.historico_respuestas + SEP + entrada
    else:
        r.historico_respuestas = entrada

    r.ultima_respuesta = body.texto.strip()
    r.updated_at = datetime.utcnow()
    db.commit()
    return _serializar(r)


@router.post("/{reclamo_id}/cerrar")
def cerrar_reclamo(reclamo_id: int, body: ResponderBody, db: Session = Depends(get_db)):
    r = db.query(Reclamo).filter(Reclamo.id == reclamo_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Reclamo no encontrado")
    r.activo = False
    r.fecha_cierre = date.today()
    r.como_se_resolvio = body.texto.strip()
    r.updated_at = datetime.utcnow()
    db.commit()
    return _serializar(r)


@router.post("/{reclamo_id}/analizar")
def analizar_con_ia(reclamo_id: int, db: Session = Depends(get_db)):
    """Call Claude to analyze claim history, suggest action plan, and draft a response email."""
    from app.db.models import Factura, Padron
    r = db.query(Reclamo).filter(Reclamo.id == reclamo_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Reclamo no encontrado")

    todos = db.query(Reclamo).filter(Reclamo.cliente_id == r.cliente_id).order_by(Reclamo.fecha_inicio).all()
    historial_texto = _formatear_historial_para_ia(todos)

    # Facturas pendientes del cliente para contexto
    facturas_pendientes = db.query(Factura).filter(
        Factura.cliente_id == r.cliente_id, Factura.saldo > 0
    ).order_by(Factura.fecha_vencimiento).all()
    facturas_txt = "\n".join(
        f"  - {f.nro_factura}: saldo ${f.saldo:,.0f}, vence {f.fecha_vencimiento}"
        for f in facturas_pendientes
    ) or "  (sin facturas pendientes)"

    padron = db.query(Padron).filter(Padron.cliente_id == r.cliente_id).first()
    razon = (padron.razon_social if padron else None) or r.cliente_id
    mail_destino = (padron.mail_reclamo_factura if padron else None) or "(mail no configurado)"

    try:
        import openai as _openai
        from app.config import settings
        _openai.api_key = settings.openai_api_key

        prompt = f"""Sos un asistente de gestion de cobranzas y atencion al cliente de TUBLOOD SA, empresa argentina.

Analiza el historial de reclamos del cliente "{razon}" y genera DOS secciones separadas con exactamente estos encabezados:

--- SECCION 1: ANALISIS ---
1. Resumen ejecutivo de la situacion del cliente
2. Evaluacion del riesgo de incobrabilidad (bajo / medio / alto) con justificacion
3. Plan de accion concreto con pasos especificos y fechas sugeridas
4. Recomendacion: accion de cobro judicial, extrajudicial, o continuar gestion amigable

--- SECCION 2: BORRADOR DE MAIL ---
Redacta un mail de respuesta al cliente para enviar a {mail_destino}.
El mail debe:
- Ser profesional y cordial pero firme
- Hacer referencia al reclamo especifico
- Proponer una solucion o proximo paso concreto
- Mencionar las facturas pendientes si corresponde:
{facturas_txt}
- Estar listo para copiar y enviar (con Asunto, cuerpo y firma de TUBLOOD SA)

Historial de reclamos:
{historial_texto}

Responde en espanol. Sin emojis."""

        resp_ia = _openai.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        respuesta = resp_ia.choices[0].message.content

        if "SECCION 2" in respuesta:
            partes = respuesta.split("--- SECCION 2")
            analisis = partes[0].replace("--- SECCION 1: ANALISIS ---", "").strip()
            email_sugerido = ("--- SECCION 2" + partes[1]).replace("--- SECCION 2: BORRADOR DE MAIL ---", "").strip() if len(partes) > 1 else ""
        else:
            analisis = respuesta
            email_sugerido = ""
    except Exception as exc:
        analisis = f"Error al conectar con la IA: {exc}. Verifica OPENAI_API_KEY en el .env."
        email_sugerido = ""

    return {
        "reclamo_id": reclamo_id,
        "cliente_id": r.cliente_id,
        "razon_social": razon,
        "total_reclamos_cliente": len(todos),
        "analisis": analisis,
        "email_sugerido": email_sugerido,
        "mail_destino": mail_destino,
    }


# ------------------------------------------------------------------

def _serializar(r: Reclamo) -> dict:
    historico = []
    if r.historico_respuestas:
        for entrada in r.historico_respuestas.split(SEP):
            partes = entrada.split("|", 1)
            historico.append({
                "fecha": partes[0].strip() if len(partes) > 1 else "",
                "texto": partes[1].strip() if len(partes) > 1 else partes[0].strip(),
            })

    return {
        "id": r.id,
        "cliente_id": r.cliente_id,
        "cuit": r.cuit,
        "descripcion": r.descripcion,
        "ultima_respuesta": r.ultima_respuesta,
        "historico": historico,
        "como_se_resolvio": r.como_se_resolvio,
        "activo": r.activo,
        "canal": r.canal,
        "fecha_inicio": str(r.fecha_inicio) if r.fecha_inicio else None,
        "fecha_cierre": str(r.fecha_cierre) if r.fecha_cierre else None,
    }


def _formatear_historial_para_ia(reclamos: List[Reclamo]) -> str:
    partes = []
    for i, r in enumerate(reclamos, 1):
        estado = "ABIERTO" if r.activo else "CERRADO"
        partes.append(
            f"Reclamo {i} [{estado}] - Inicio: {r.fecha_inicio} - Cierre: {r.fecha_cierre or 'en curso'}\n"
            f"Descripcion: {r.descripcion}\n"
            f"Ultima respuesta al cliente: {r.ultima_respuesta}\n"
            f"Como se resolvio: {r.como_se_resolvio or 'Sin resolucion aun'}\n"
            f"Historico:\n{_historial_legible(r.historico_respuestas)}"
        )
    return "\n\n---\n\n".join(partes)


def _historial_legible(historico: Optional[str]) -> str:
    if not historico:
        return "  (sin entradas)"
    lineas = []
    for entrada in historico.split(SEP):
        partes = entrada.split("|", 1)
        if len(partes) == 2:
            lineas.append(f"  [{partes[0].strip()}] {partes[1].strip()}")
        else:
            lineas.append(f"  {entrada.strip()}")
    return "\n".join(lineas)
