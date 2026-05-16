from pathlib import Path
from datetime import date
from app.db.models import Factura, MovimientoBanco, Conciliacion, Padron
from app.services.conciliation import ingestar_movimientos, conciliar_banco, facturas_vencidas
from app.services.ingestion import cargar_facturas, cargar_padron

FIXTURES = Path(__file__).parent.parent / "fixtures"
LIBRO3 = FIXTURES / "Libro3_test.xlsx"
MACRO_FILE = FIXTURES / "movimientos_macro_test.xlsx"
GALICIA_FILE = FIXTURES / "movimientos_galicia_test.xlsx"


def _seed_macro(db):
    cargar_facturas(db, filepath=LIBRO3)
    cargar_padron(db)
    ingestar_movimientos(db, MACRO_FILE, banco="macro")


def _seed_galicia(db):
    cargar_facturas(db, filepath=LIBRO3)
    cargar_padron(db)
    ingestar_movimientos(db, GALICIA_FILE, banco="galicia")


def _seed_both(db):
    cargar_facturas(db, filepath=LIBRO3)
    cargar_padron(db)
    ingestar_movimientos(db, MACRO_FILE, banco="macro")
    ingestar_movimientos(db, GALICIA_FILE, banco="galicia")


class TestIngestarMovimientos:
    def test_inserta_macro(self, db):
        count = ingestar_movimientos(db, MACRO_FILE, banco="macro")
        assert count == 4  # 3 con CUIT + 1 sin CUIT; debito excluido

    def test_inserta_galicia(self, db):
        count = ingestar_movimientos(db, GALICIA_FILE, banco="galicia")
        # 4 creditos en fixture (debito excluido)
        assert count == 4

    def test_idempotente_macro(self, db):
        ingestar_movimientos(db, MACRO_FILE, banco="macro")
        assert ingestar_movimientos(db, MACRO_FILE, banco="macro") == 0

    def test_idempotente_galicia(self, db):
        ingestar_movimientos(db, GALICIA_FILE, banco="galicia")
        assert ingestar_movimientos(db, GALICIA_FILE, banco="galicia") == 0

    def test_banco_field_guardado(self, db):
        ingestar_movimientos(db, MACRO_FILE, banco="macro")
        ingestar_movimientos(db, GALICIA_FILE, banco="galicia")
        macros = db.query(MovimientoBanco).filter(MovimientoBanco.banco == "macro").count()
        galicias = db.query(MovimientoBanco).filter(MovimientoBanco.banco == "galicia").count()
        assert macros == 4
        assert galicias == 4

    def test_cuit_extraido_macro(self, db):
        ingestar_movimientos(db, MACRO_FILE, banco="macro")
        con_cuit = db.query(MovimientoBanco).filter(
            MovimientoBanco.banco == "macro",
            MovimientoBanco.cuit_extraido.isnot(None)
        ).count()
        assert con_cuit == 3

    def test_cuit_extraido_galicia(self, db):
        ingestar_movimientos(db, GALICIA_FILE, banco="galicia")
        con_cuit = db.query(MovimientoBanco).filter(
            MovimientoBanco.banco == "galicia",
            MovimientoBanco.cuit_extraido.isnot(None)
        ).count()
        assert con_cuit == 4  # todos los creditos tienen CUIT en el fixture


class TestConciliarBancoMacro:
    def test_genera_conciliaciones(self, db):
        _seed_macro(db)
        results = conciliar_banco(db)
        assert len(results) > 0

    def test_fifo_cobra_mas_antigua_primero(self, db):
        _seed_macro(db)
        conciliar_banco(db)
        # F-MAC-001 vence 2026-02-09, importe exacto 4400 -> debe quedar saldo=0
        f = db.query(Factura).filter(Factura.nro_factura == "F-MAC-001").first()
        assert f.saldo == 0
        assert f.estado == "cobrado"

    def test_movimientos_marcados_procesado(self, db):
        _seed_macro(db)
        conciliar_banco(db)
        procesados = db.query(MovimientoBanco).filter(
            MovimientoBanco.cuit_extraido.isnot(None),
            MovimientoBanco.banco == "macro"
        ).all()
        assert all(m.procesado for m in procesados)

    def test_tolerancia_10pct(self, db):
        _seed_macro(db)
        results = conciliar_banco(db, tolerance=0.10)
        # F-MAC-002: saldo=14500, movimiento=14000 -> dentro del 10% (14000 >= 14500*0.9=13050)
        mac002_results = [r for r in results if r["nro_factura"] == "F-MAC-002"]
        assert len(mac002_results) > 0
        assert mac002_results[0]["estado"] == "cobrado_total"


class TestConciliarBancoGalicia:
    def test_genera_conciliaciones_galicia(self, db):
        _seed_galicia(db)
        results = conciliar_banco(db)
        assert len(results) > 0

    def test_galicia_match_99k(self, db):
        _seed_galicia(db)
        conciliar_banco(db)
        # F-GAL-001: saldo=100000, credito galicia=99030.12 -> dentro 10%
        f = db.query(Factura).filter(Factura.nro_factura == "F-GAL-001").first()
        assert f.saldo == 0
        assert f.estado == "cobrado"

    def test_galicia_match_23k(self, db):
        _seed_galicia(db)
        conciliar_banco(db)
        # F-GAL-002: saldo=23000, credito=23146.62 -> dentro 10%
        f = db.query(Factura).filter(Factura.nro_factura == "F-GAL-002").first()
        assert f.saldo == 0


class TestConciliarAmbos:
    def test_ambos_bancos_concilian_independiente(self, db):
        _seed_both(db)
        results = conciliar_banco(db)
        cobradas = db.query(Factura).filter(Factura.estado == "cobrado").count()
        assert cobradas >= 3

    def test_sin_doble_procesamiento(self, db):
        _seed_both(db)
        conciliar_banco(db)
        count1 = db.query(Conciliacion).count()
        conciliar_banco(db)  # segunda corrida no debe agregar nada
        count2 = db.query(Conciliacion).count()
        assert count1 == count2


class TestFacturasVencidas:
    def test_retorna_solo_vencidas(self, db):
        cargar_facturas(db, filepath=LIBRO3)
        vencidas = facturas_vencidas(db, mora_minima=0)
        hoy = date.today()
        assert all(f.fecha_vencimiento < hoy for f in vencidas)

    def test_con_saldo_cero_excluidas(self, db):
        cargar_facturas(db, filepath=LIBRO3)
        f = db.query(Factura).first()
        f.saldo = 0
        db.commit()
        ids = [v.id for v in facturas_vencidas(db, mora_minima=0)]
        assert f.id not in ids
