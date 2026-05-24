import json
import httpx
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.models import RiesgoCrediticio

BCRA_BASE = "https://api.bcra.gob.ar/centraldeudores/v1.0"
CACHE_HORAS = 24

SITUACION_LABEL = {
    0: "Sin datos",
    1: "Normal",
    2: "Riesgo bajo",
    3: "Con problemas",
    4: "Alto riesgo",
    5: "Irrecuperable",
    6: "Irrecuperable",
}

SITUACION_COLOR = {
    0: "gris",
    1: "verde",
    2: "verde",
    3: "amarillo",
    4: "rojo",
    5: "rojo",
    6: "rojo",
}


def _limpiar_cuit(cuit: str) -> str:
    return cuit.replace("-", "").replace(" ", "").strip()


def _consultar_bcra(cuit: str) -> dict:
    try:
        resp = httpx.get(f"{BCRA_BASE}/Deudas/{cuit}", timeout=10, verify=False)
        if resp.status_code == 404:
            return {"situacion": 1, "denominacion": "", "raw": {}}
        if resp.status_code == 200:
            data = resp.json()
            resultados = data.get("results", {})
            periodos = resultados.get("periodos", [])
            situacion_max = 1
            for periodo in periodos:
                for entidad in periodo.get("entidades", []):
                    s = entidad.get("situacion", 1)
                    if s > situacion_max:
                        situacion_max = s
            return {
                "situacion": situacion_max,
                "denominacion": resultados.get("denominacion", ""),
                "raw": data,
            }
        return {"situacion": 0, "denominacion": "", "raw": {"error": f"HTTP {resp.status_code}"}}
    except Exception as exc:
        return {"situacion": 0, "denominacion": "", "raw": {"error": str(exc)}}


def get_riesgo(cuit: str, db: Session, forzar: bool = False) -> dict:
    cuit = _limpiar_cuit(cuit)
    limite_cache = datetime.utcnow() - timedelta(hours=CACHE_HORAS)

    if not forzar:
        cached = (
            db.query(RiesgoCrediticio)
            .filter(
                RiesgoCrediticio.cuit == cuit,
                RiesgoCrediticio.activo == True,
                RiesgoCrediticio.fecha_consulta >= limite_cache,
            )
            .first()
        )
        if cached:
            return _serializar(cached, desde_cache=True)

    resultado = _consultar_bcra(cuit)

    db.query(RiesgoCrediticio).filter(RiesgoCrediticio.cuit == cuit).update({"activo": False})

    nuevo = RiesgoCrediticio(
        cuit=cuit,
        situacion=resultado["situacion"],
        denominacion=resultado.get("denominacion", ""),
        detalle=json.dumps(resultado.get("raw", {})),
        activo=True,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return _serializar(nuevo, desde_cache=False)


def get_riesgo_bulk(cuits: list[str], db: Session) -> dict[str, dict]:
    cuits = [_limpiar_cuit(c) for c in cuits if c]
    if not cuits:
        return {}
    limite_cache = datetime.utcnow() - timedelta(hours=CACHE_HORAS)
    registros = (
        db.query(RiesgoCrediticio)
        .filter(
            RiesgoCrediticio.cuit.in_(cuits),
            RiesgoCrediticio.activo == True,
            RiesgoCrediticio.fecha_consulta >= limite_cache,
        )
        .all()
    )
    return {r.cuit: _serializar(r, desde_cache=True) for r in registros}


def _serializar(r: RiesgoCrediticio, desde_cache: bool = True) -> dict:
    return {
        "cuit": r.cuit,
        "situacion": r.situacion,
        "label": SITUACION_LABEL.get(r.situacion, "Desconocido"),
        "color": SITUACION_COLOR.get(r.situacion, "gris"),
        "alerta": r.situacion >= 3,
        "denominacion": r.denominacion or "",
        "fecha_consulta": r.fecha_consulta.strftime("%Y-%m-%d %H:%M") if r.fecha_consulta else "",
        "desde_cache": desde_cache,
    }
