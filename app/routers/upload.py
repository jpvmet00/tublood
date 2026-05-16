import shutil
import tempfile
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.adapters.factory import detect_banco, get_adapter
from app.services.conciliation import ingestar_movimientos, conciliar_banco
from app.services.ingestion import cargar_facturas, cargar_padron, upsert_padron_desde_excel

router = APIRouter(prefix="/upload", tags=["upload"])


def _save_temp(file: UploadFile) -> Path:
    suffix = Path(file.filename).suffix if file.filename else ".xls"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    shutil.copyfileobj(file.file, tmp)
    tmp.close()
    return Path(tmp.name)


@router.post("/banco/detect")
def detect_banco_endpoint(file: UploadFile = File(...)):
    """Detect bank from uploaded file. Does NOT persist anything."""
    tmp_path = _save_temp(file)
    try:
        info = detect_banco(tmp_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        tmp_path.unlink(missing_ok=True)
    return info


@router.post("/banco")
def upload_banco(
    file: UploadFile = File(...),
    banco: str = Form("macro"),
    db: Session = Depends(get_db),
):
    """Upload one bank file, ingest credits, and run conciliation."""
    tmp_path = _save_temp(file)
    try:
        result = ingestar_movimientos(db, tmp_path, banco=banco)
        conciliados = conciliar_banco(db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        tmp_path.unlink(missing_ok=True)

    return {
        "movimientos_insertados": result["insertados"],
        "ya_procesado": result["ya_procesado"],
        "fecha_desde": result["fecha_desde"],
        "fecha_hasta": result["fecha_hasta"],
        "conciliaciones_generadas": len(conciliados),
        "detalle": conciliados,
    }


@router.post("/banco/multi")
def upload_banco_multi(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Upload multiple bank files at once. Auto-detects each bank, ingests, then conciliates."""
    total_insertados = 0
    archivos_procesados = []
    errores = []

    tmp_paths = []
    for file in files:
        tmp_path = _save_temp(file)
        tmp_paths.append((file.filename, tmp_path))

    try:
        for filename, tmp_path in tmp_paths:
            try:
                info = detect_banco(tmp_path)
                banco_id = info["banco_id"]
                result = ingestar_movimientos(db, tmp_path, banco=banco_id)
                total_insertados += result["insertados"]
                archivos_procesados.append({
                    "archivo": filename,
                    "banco": info["descripcion"],
                    "movimientos_insertados": result["insertados"],
                    "ya_procesado": result["ya_procesado"],
                    "fecha_desde": result["fecha_desde"],
                    "fecha_hasta": result["fecha_hasta"],
                })
            except Exception as exc:
                errores.append({"archivo": filename, "error": str(exc)})
    finally:
        for _, tmp_path in tmp_paths:
            tmp_path.unlink(missing_ok=True)

    conciliados = conciliar_banco(db)

    return {
        "archivos_procesados": archivos_procesados,
        "errores": errores,
        "movimientos_insertados_total": total_insertados,
        "conciliaciones_generadas": len(conciliados),
        "detalle": conciliados,
    }


@router.post("/facturas")
def upload_facturas(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload Libro3.xlsx and reload all facturas."""
    tmp_path = _save_temp(file)
    try:
        count = cargar_facturas(db, filepath=tmp_path)
        cargar_padron(db)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        tmp_path.unlink(missing_ok=True)

    return {"facturas_procesadas": count}


@router.post("/padron")
def upload_padron(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload Excel con columnas CUIT, RAZON_SOCIAL (opt), CLIENTE_ID (opt).

    Crea o actualiza entradas del padron. Columnas reconocidas:
    CUIT / RAZON_SOCIAL / RAZON / CLIENTE_ID / CLIENTE / NOMBRE
    """
    tmp_path = _save_temp(file)
    try:
        result = upsert_padron_desde_excel(db, filepath=tmp_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        tmp_path.unlink(missing_ok=True)

    return result


@router.get("/padron")
def get_padron(db: Session = Depends(get_db)):
    """Return all padron entries."""
    from app.db.models import Padron
    entries = db.query(Padron).order_by(Padron.razon_social).all()
    return [
        {
            "cuit": p.cuit,
            "razon_social": p.razon_social,
            "cliente_id": p.cliente_id,
            "activo": p.activo,
        }
        for p in entries
    ]


@router.get("/facturas")
def get_facturas(db: Session = Depends(get_db)):
    """Return all facturas with key fields for display."""
    from app.db.models import Factura
    from datetime import date as date_cls
    hoy = date_cls.today()
    facturas = db.query(Factura).order_by(Factura.fecha_vencimiento.asc().nullsfirst()).all()
    result = []
    for f in facturas:
        if f.fecha_vencimiento:
            dias_para_vencer = (f.fecha_vencimiento - hoy).days
        else:
            dias_para_vencer = None
        result.append({
            "nro_factura": f.nro_factura,
            "razon_social": f.razon_social,
            "cliente_id": f.cliente_id,
            "cuit": f.cuit,
            "importe_original": f.importe_original,
            "saldo": f.saldo,
            "fecha_emision": str(f.fecha_emision) if f.fecha_emision else None,
            "fecha_vencimiento": str(f.fecha_vencimiento) if f.fecha_vencimiento else None,
            "condicion_venta": f.condicion_venta,
            "dias_para_vencer": dias_para_vencer,
            "estado": f.estado,
            "vencida": bool(f.fecha_vencimiento and f.fecha_vencimiento < hoy and f.saldo > 0),
        })
    return result


@router.post("/reclamos")
def upload_reclamos(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload Excel con reclamos. Upsert por (cliente_id, descripcion)."""
    import pandas as pd
    import numpy as np
    from datetime import date as date_cls
    from app.db.models import Reclamo

    tmp_path = _save_temp(file)
    try:
        df = pd.read_excel(tmp_path)
        df.columns = [str(c).strip().upper().replace(" ", "_") for c in df.columns]

        _col_map = {
            "CLIENTE_ID":           "cliente_id",
            "CLIENTE":              "cliente_id",
            "CUIT":                 "cuit",
            "RAZON_SOCIAL":         "razon_social",
            "DESCRIPCION":          "descripcion",
            "ULTIMA_RTA_AL_CLIENTE":"ultima_respuesta",
            "ULTIMA_RESPUESTA":     "ultima_respuesta",
            "HISTORICO_RESPUESTAS": "historico_respuestas",
            "COMO_SE_RESOLVIO":     "como_se_resolvio",
            "ACTIVO":               "activo",
            "FECHA_INICIO":         "fecha_inicio",
            "FECHA_CIERRE":         "fecha_cierre",
        }
        df = df.rename(columns={k: v for k, v in _col_map.items() if k in df.columns})

        creados = 0
        actualizados = 0

        for _, row in df.iterrows():
            cliente = _safe_str_val(row.get("cliente_id"))
            if not cliente:
                continue

            descripcion = _safe_str_val(row.get("descripcion"))
            existing = (
                db.query(Reclamo)
                .filter(Reclamo.cliente_id == cliente, Reclamo.descripcion == descripcion)
                .first()
            )

            activo_val = row.get("activo")
            if activo_val is None or (isinstance(activo_val, float) and np.isnan(activo_val)):
                activo_val = True
            else:
                activo_val = bool(activo_val)

            fecha_inicio = _safe_date_val(row.get("fecha_inicio"))
            fecha_cierre = _safe_date_val(row.get("fecha_cierre"))

            if existing:
                existing.ultima_respuesta   = _safe_str_val(row.get("ultima_respuesta")) or existing.ultima_respuesta
                existing.historico_respuestas = _safe_str_val(row.get("historico_respuestas")) or existing.historico_respuestas
                existing.como_se_resolvio   = _safe_str_val(row.get("como_se_resolvio")) or existing.como_se_resolvio
                existing.activo             = activo_val
                if fecha_cierre:
                    existing.fecha_cierre = fecha_cierre
                actualizados += 1
            else:
                db.add(Reclamo(
                    cliente_id          = cliente,
                    cuit                = _safe_str_val(row.get("cuit")),
                    descripcion         = descripcion,
                    ultima_respuesta    = _safe_str_val(row.get("ultima_respuesta")),
                    historico_respuestas= _safe_str_val(row.get("historico_respuestas")),
                    como_se_resolvio    = _safe_str_val(row.get("como_se_resolvio")),
                    activo              = activo_val,
                    fecha_inicio        = fecha_inicio or date_cls.today(),
                    fecha_cierre        = fecha_cierre,
                ))
                creados += 1

        db.commit()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        tmp_path.unlink(missing_ok=True)

    return {"creados": creados, "actualizados": actualizados, "total": creados + actualizados}


def _safe_str_val(val) -> str:
    import numpy as np
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    s = str(val).strip()
    return s if s and s.lower() != "nan" else None


def _safe_date_val(val):
    import pandas as pd
    if val is None:
        return None
    try:
        if pd.isnull(val):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(val, "date"):
        return val.date()
    try:
        return pd.to_datetime(val).date()
    except Exception:
        return None
