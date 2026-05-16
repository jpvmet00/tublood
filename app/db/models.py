from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, Boolean, Text, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime


class Base(DeclarativeBase):
    pass


class Factura(Base):
    __tablename__ = "facturas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nro_factura = Column(String(50), nullable=False)
    cliente_id = Column(String(100), nullable=False)
    razon_social = Column(String(300), nullable=True)
    cuit = Column(String(20), nullable=True)
    importe_original = Column(Float, nullable=False)
    saldo = Column(Float, nullable=False)
    fecha_emision = Column(Date, nullable=True)
    fecha_vencimiento = Column(Date, nullable=True)
    condicion_venta = Column(String(50), nullable=True)
    vendedor = Column(String(200), nullable=True)
    email_vendedor = Column(String(200), nullable=True)
    estado = Column(String(50), default="pendiente")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conciliaciones = relationship("Conciliacion", back_populates="factura")
    reclamos = relationship("Reclamo", back_populates="factura")

    __table_args__ = (
        UniqueConstraint("nro_factura", "cliente_id", name="uq_factura_cliente"),
    )


class MovimientoBanco(Base):
    __tablename__ = "movimientos_banco"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha = Column(Date, nullable=False)
    concepto = Column(Text, nullable=True)
    importe = Column(Float, nullable=False)
    cuit_extraido = Column(String(20), nullable=True)
    razon_social = Column(String(300), nullable=True)
    banco = Column(String(50), nullable=False)
    referencia = Column(String(200), nullable=True)
    procesado = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    conciliaciones = relationship("Conciliacion", back_populates="movimiento")


class Conciliacion(Base):
    __tablename__ = "conciliaciones"

    id = Column(Integer, primary_key=True, autoincrement=True)
    factura_id = Column(Integer, ForeignKey("facturas.id"), nullable=False)
    movimiento_id = Column(Integer, ForeignKey("movimientos_banco.id"), nullable=True)
    importe_aplicado = Column(Float, nullable=False)
    estado = Column(String(50), nullable=False)  # cobrado_total | cobrado_parcial | sin_cobro
    metodo = Column(String(50), default="home_banking")  # home_banking | manual
    fecha_conciliacion = Column(DateTime, default=datetime.utcnow)

    factura = relationship("Factura", back_populates="conciliaciones")
    movimiento = relationship("MovimientoBanco", back_populates="conciliaciones")


class Padron(Base):
    __tablename__ = "padron"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cuit = Column(String(20), unique=True, nullable=False)
    razon_social = Column(String(300), nullable=True)
    cliente_id = Column(String(100), nullable=True)
    activo = Column(Boolean, default=True)
    mail_reclamo_factura = Column(String(200), nullable=True)
    mail_atencion_cliente = Column(String(200), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Reclamo(Base):
    __tablename__ = "reclamos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cuit = Column(String(20), nullable=True)
    cliente_id = Column(String(100), nullable=False)
    factura_id = Column(Integer, ForeignKey("facturas.id"), nullable=True)
    descripcion = Column(Text, nullable=True)
    ultima_respuesta = Column(Text, nullable=True)
    historico_respuestas = Column(Text, nullable=True)   # entradas separadas por |||
    como_se_resolvio = Column(Text, nullable=True)
    activo = Column(Boolean, default=True)
    canal = Column(String(50), default="email")
    fecha_inicio = Column(Date, nullable=True)
    fecha_cierre = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    factura = relationship("Factura", back_populates="reclamos")
