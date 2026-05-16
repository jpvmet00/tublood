"""Load Excel data files into the DB."""
import re
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session
from app.db.models import Factura, Padron
from app.config import settings

# Libro3 real column mapping
_LIBRO3_RENAME = {
    # real columns -> canonical
    "NUM":             "nro_factura",
    "CLIENTE":         "cliente_id",
    "RAZON":           "razon_social",
    "TOTAL":           "importe_original",
    "SALDO":           "saldo",
    "FECHA":           "fecha_emision",
    "nombre_vendedor": "vendedor",
    # optional / may not exist
    "NRO":             "nro_factura",   # fallback nombre de columna
    "CUIT":            "cuit",
    "VENCIMIENTO":     "fecha_vencimiento",
    "CONDICION":       "condicion_venta",
    "EMAIL":           "email_vendedor",
}


def cargar_facturas(db: Session, filepath: Optional[Path] = None) -> int:
    """Read Libro3.xlsx (sheet pendientes) and upsert into facturas table.

    Handles both the real Libro3 column layout and the test fixture layout.
    Returns the number of rows processed.
    """
    path = filepath or settings.data_dir / "Libro3.xlsx"
    df = pd.read_excel(path, sheet_name="pendientes")
    df.columns = [str(c).strip() for c in df.columns]

    df = df.rename(columns={k: v for k, v in _LIBRO3_RENAME.items() if k in df.columns})

    for col in ("fecha_emision", "fecha_vencimiento"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

    for col in ("importe_original", "saldo"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    count = 0
    for _, row in df.iterrows():
        nro = _safe_str(row.get("nro_factura"))
        cliente = _safe_str(row.get("cliente_id"))
        if not nro or not cliente:
            continue

        existing = (
            db.query(Factura)
            .filter(Factura.nro_factura == nro, Factura.cliente_id == cliente)
            .first()
        )

        data = {
            "nro_factura":    nro,
            "cliente_id":     cliente,
            "razon_social":   _safe_str(row.get("razon_social")),
            "cuit":           _safe_str(row.get("cuit")),
            "importe_original": float(row.get("importe_original", 0)),
            "saldo":          float(row.get("saldo", 0)),
            "fecha_emision":  _safe_date(row.get("fecha_emision")),
            "fecha_vencimiento": _safe_date(row.get("fecha_vencimiento")),
            "condicion_venta": _safe_str(row.get("condicion_venta")),
            "vendedor":       _safe_str(row.get("vendedor")),
            "email_vendedor": _safe_str(row.get("email_vendedor")),
        }

        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
        else:
            db.add(Factura(**data))

        count += 1

    db.commit()
    return count


def cargar_padron(db: Session, filepath: Optional[Path] = None) -> int:
    """Build padron entries from facturas that have a CUIT."""
    count = 0
    for factura in db.query(Factura).filter(Factura.cuit.isnot(None)):
        cuit = str(factura.cuit).strip()
        if not cuit:
            continue
        if not db.query(Padron).filter(Padron.cuit == cuit).first():
            db.add(Padron(
                cuit=cuit,
                cliente_id=factura.cliente_id,
                razon_social=factura.razon_social,
            ))
            count += 1
    db.commit()
    return count


def construir_padron_desde_movimientos(db: Session) -> int:
    """Match bank movements (that have razon_social) to facturas by normalized name.

    This is the main way to build the CUIT -> cliente_id link when Libro3
    does not include a CUIT column. Uses razon_social from bank movements
    (extracted by GaliciaAdapter) and matches against factura.razon_social.
    """
    from app.db.models import MovimientoBanco

    movs = (
        db.query(MovimientoBanco)
        .filter(
            MovimientoBanco.cuit_extraido.isnot(None),
            MovimientoBanco.razon_social.isnot(None),
        )
        .all()
    )

    count = 0
    for mov in movs:
        cuit = mov.cuit_extraido
        razon_mov = _normalizar_razon(mov.razon_social)

        existing = db.query(Padron).filter(Padron.cuit == cuit).first()

        # Try to find matching factura by razon_social
        facturas = db.query(Factura).filter(Factura.razon_social.isnot(None)).all()
        match = None
        for f in facturas:
            if _normalizar_razon(f.razon_social) == razon_mov:
                match = f
                break

        if existing:
            # Update only if we found new info
            if match and not existing.cliente_id:
                existing.cliente_id = match.cliente_id
                existing.razon_social = match.razon_social
        else:
            db.add(Padron(
                cuit=cuit,
                cliente_id=match.cliente_id if match else None,
                razon_social=match.razon_social if match else mov.razon_social,
            ))
            count += 1

    try:
        db.commit()
    except Exception:
        db.rollback()

    return count


def upsert_padron_desde_excel(db: Session, filepath: Path) -> dict:
    """Read an Excel with columns CUIT (required), RAZON_SOCIAL (opt), CLIENTE_ID (opt).

    Recognized column names (case-insensitive):
      CUIT
      RAZON_SOCIAL / RAZON / RAZON SOCIAL / NOMBRE
      CLIENTE_ID / CLIENTE / ID_CLIENTE
    """
    df = pd.read_excel(filepath)
    df.columns = [str(c).strip().upper().replace(" ", "_") for c in df.columns]

    _col_map = {
        "CUIT":                  "cuit",
        "RAZON_SOCIAL":          "razon_social",
        "RAZON":                 "razon_social",
        "NOMBRE":                "razon_social",
        "CLIENTE_ID":            "cliente_id",
        "CLIENTE":               "cliente_id",
        "ID_CLIENTE":            "cliente_id",
        "MAIL_RECLAMO_FACTURA":  "mail_reclamo_factura",
        "MAIL_ATENCION_CLIENTE": "mail_atencion_cliente",
    }
    df = df.rename(columns={k: v for k, v in _col_map.items() if k in df.columns})

    if "cuit" not in df.columns:
        raise ValueError("El archivo debe tener una columna CUIT.")

    creados = 0
    actualizados = 0

    for _, row in df.iterrows():
        cuit = _safe_str(row.get("cuit"))
        if not cuit:
            continue
        # normalize: strip non-digits
        cuit = re.sub(r"\D", "", cuit)
        if not cuit:
            continue

        razon = _safe_str(row.get("razon_social"))
        cliente = _safe_str(row.get("cliente_id"))

        mail_reclamo = _safe_str(row.get("mail_reclamo_factura"))
        mail_atencion = _safe_str(row.get("mail_atencion_cliente"))

        existing = db.query(Padron).filter(Padron.cuit == cuit).first()
        if existing:
            if razon:
                existing.razon_social = razon
            if cliente:
                existing.cliente_id = cliente
            if mail_reclamo:
                existing.mail_reclamo_factura = mail_reclamo
            if mail_atencion:
                existing.mail_atencion_cliente = mail_atencion
            actualizados += 1
        else:
            db.add(Padron(
                cuit=cuit,
                razon_social=razon,
                cliente_id=cliente,
                mail_reclamo_factura=mail_reclamo,
                mail_atencion_cliente=mail_atencion,
            ))
            creados += 1

    db.commit()
    return {"creados": creados, "actualizados": actualizados, "total": creados + actualizados}


# ------------------------------------------------------------------

_SUFIJOS = re.compile(
    r"\b(S\.?A\.?|S\.?R\.?L\.?|S\.?A\.?S\.?|S\.?C\.?|LTDA\.?|INC\.?|LLC\.?)\b",
    re.IGNORECASE,
)


def _normalizar_razon(razon: Optional[str]) -> str:
    if not razon:
        return ""
    r = razon.upper().strip()
    r = _SUFIJOS.sub("", r)
    r = re.sub(r"[^A-Z0-9 ]", " ", r)
    return re.sub(r"\s+", " ", r).strip()


def _safe_str(val) -> Optional[str]:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    s = str(val).strip()
    return s if s else None


def _safe_date(val):
    if val is None:
        return None
    try:
        if pd.isnull(val):
            return None
    except (TypeError, ValueError):
        pass
    return val
