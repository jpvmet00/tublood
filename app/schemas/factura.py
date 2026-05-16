from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional


class FacturaBase(BaseModel):
    nro_factura: str
    cliente_id: str
    cuit: Optional[str] = None
    importe_original: float
    saldo: float
    fecha_emision: Optional[date] = None
    fecha_vencimiento: Optional[date] = None
    condicion_venta: Optional[str] = None
    vendedor: Optional[str] = None
    email_vendedor: Optional[str] = None


class FacturaOut(FacturaBase):
    id: int
    estado: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ConciliacionOut(BaseModel):
    factura_id: int
    movimiento_id: Optional[int]
    importe_aplicado: float
    estado: str
    metodo: str
    fecha_conciliacion: datetime

    model_config = {"from_attributes": True}


class ReclamoOut(BaseModel):
    id: int
    factura_id: int
    cliente_id: str
    fecha_reclamo: datetime
    canal: str
    resultado: Optional[str]

    model_config = {"from_attributes": True}
