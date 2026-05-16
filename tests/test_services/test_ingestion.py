from pathlib import Path
from app.db.models import Factura, Padron
from app.services.ingestion import cargar_facturas, cargar_padron

FIXTURES = Path(__file__).parent.parent / "fixtures"
LIBRO3 = FIXTURES / "Libro3_test.xlsx"


class TestCargarFacturas:
    def test_carga_todas_las_filas(self, db):
        count = cargar_facturas(db, filepath=LIBRO3)
        assert count == 6  # 3 Macro + 3 Galicia

    def test_datos_correctos_macro(self, db):
        cargar_facturas(db, filepath=LIBRO3)
        f = db.query(Factura).filter(Factura.nro_factura == "F-MAC-001").first()
        assert f is not None
        assert f.cliente_id == "CLI-MACRO-A"
        assert f.saldo == 4400
        assert f.cuit == "27218826488"

    def test_datos_correctos_galicia(self, db):
        cargar_facturas(db, filepath=LIBRO3)
        f = db.query(Factura).filter(Factura.nro_factura == "F-GAL-001").first()
        assert f is not None
        assert f.cliente_id == "INSTITUTO DATA SCIENCE"
        assert f.saldo == 100000
        assert f.cuit == "30717199002"

    def test_upsert_actualiza_saldo(self, db):
        cargar_facturas(db, filepath=LIBRO3)
        f = db.query(Factura).filter(Factura.nro_factura == "F-MAC-001").first()
        f.saldo = 1
        db.commit()
        cargar_facturas(db, filepath=LIBRO3)
        db.expire(f)
        assert f.saldo == 4400

    def test_idempotente(self, db):
        cargar_facturas(db, filepath=LIBRO3)
        cargar_facturas(db, filepath=LIBRO3)
        assert db.query(Factura).count() == 6


class TestCargarPadron:
    def test_crea_entradas_de_cuit(self, db):
        cargar_facturas(db, filepath=LIBRO3)
        count = cargar_padron(db)
        # 6 filas pero CUIT 30717199002 aparece 2 veces -> 5 CUITs unicos
        assert count == 5

    def test_no_duplica_en_segunda_carga(self, db):
        cargar_facturas(db, filepath=LIBRO3)
        cargar_padron(db)
        assert cargar_padron(db) == 0

    def test_cliente_id_enlazado_macro(self, db):
        cargar_facturas(db, filepath=LIBRO3)
        cargar_padron(db)
        p = db.query(Padron).filter(Padron.cuit == "27218826488").first()
        assert p is not None
        assert p.cliente_id == "CLI-MACRO-A"

    def test_cliente_id_enlazado_galicia(self, db):
        cargar_facturas(db, filepath=LIBRO3)
        cargar_padron(db)
        p = db.query(Padron).filter(Padron.cuit == "30717199002").first()
        assert p is not None
        assert p.cliente_id == "INSTITUTO DATA SCIENCE"
