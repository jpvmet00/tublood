from pydantic import BaseModel, field_validator
from datetime import date
from typing import Optional


class MovimientoCanonical(BaseModel):
    fecha: date
    concepto: str
    importe: float
    cuit_extraido: Optional[str] = None
    razon_social: Optional[str] = None
    banco: str
    referencia: Optional[str] = None

    @field_validator("importe")
    @classmethod
    def importe_positivo(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("importe debe ser mayor a cero")
        return v

    @field_validator("cuit_extraido")
    @classmethod
    def normalizar_cuit(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return v.replace("-", "").strip()
