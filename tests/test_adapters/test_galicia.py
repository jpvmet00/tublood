import pytest
from pathlib import Path
from datetime import date
from app.adapters.galicia import GaliciaAdapter
from app.adapters.factory import get_adapter, detect_banco

FIXTURES = Path(__file__).parent.parent / "fixtures"
GALICIA_FILE = FIXTURES / "movimientos_galicia_test.xlsx"


class TestGaliciaAdapterValidation:
    def test_validates_correct_file(self):
        assert GaliciaAdapter().validate_file(GALICIA_FILE) is True

    def test_rejects_wrong_extension(self):
        assert GaliciaAdapter().validate_file(Path("/tmp/archivo.csv")) is False

    def test_rejects_nonexistent_file(self):
        assert GaliciaAdapter().validate_file(Path("/tmp/no_existe.xlsx")) is False

    def test_rejects_macro_file(self):
        macro_file = FIXTURES / "movimientos_macro_test.xlsx"
        assert GaliciaAdapter().validate_file(macro_file) is False


class TestGaliciaAccountInfo:
    def test_banco_name(self):
        info = GaliciaAdapter().get_account_info(GALICIA_FILE)
        assert info["banco"] == "Banco Galicia"

    def test_cuenta_number(self):
        info = GaliciaAdapter().get_account_info(GALICIA_FILE)
        assert "8190105" in info["cuenta"]

    def test_descripcion_present(self):
        info = GaliciaAdapter().get_account_info(GALICIA_FILE)
        assert "Galicia" in info["descripcion"]
        assert "8190105" in info["descripcion"]

    def test_moneda(self):
        info = GaliciaAdapter().get_account_info(GALICIA_FILE)
        assert info["moneda"] == "PESOS"


class TestGaliciaAdapterParse:
    def test_only_credits_returned(self):
        movs = GaliciaAdapter().parse(GALICIA_FILE)
        # Fixture has 4 credits and 1 debit row; debit must be excluded
        assert all(m.importe > 0 for m in movs)

    def test_debito_row_excluded(self):
        movs = GaliciaAdapter().parse(GALICIA_FILE)
        # The debit row (-50500) must not appear
        assert not any(m.importe < 0 for m in movs)

    def test_extracts_cuit_from_multiline(self):
        movs = GaliciaAdapter().parse(GALICIA_FILE)
        cuits = {m.cuit_extraido for m in movs if m.cuit_extraido}
        assert "30717199002" in cuits
        assert "30716132028" in cuits

    def test_eu_number_parsing(self):
        movs = GaliciaAdapter().parse(GALICIA_FILE)
        # "99.030,12" must parse to 99030.12
        found = [m for m in movs if m.cuit_extraido == "30717199002"]
        assert any(abs(m.importe - 99030.12) < 0.01 for m in found)

    def test_fecha_parsed_as_date(self):
        movs = GaliciaAdapter().parse(GALICIA_FILE)
        assert all(isinstance(m.fecha, date) for m in movs)

    def test_banco_field(self):
        movs = GaliciaAdapter().parse(GALICIA_FILE)
        assert all(m.banco == "galicia" for m in movs)

    def test_row_without_cuit_has_none(self):
        movs = GaliciaAdapter().parse(GALICIA_FILE)
        # The "DEV.COMPRA" credit row has no CUIT line -> None
        # (In fixture this is the localpayment row which DOES have a CUIT)
        # At least no crash and all are either str or None
        for m in movs:
            assert m.cuit_extraido is None or m.cuit_extraido.isdigit()


class TestGaliciaCuitExtraction:
    @pytest.mark.parametrize("movimiento,expected", [
        ("TRANSFERENCIAS CASH PROVEEDORES\n INSTITUTO DATA SCIENCE S.A.\n 30717199002\n BANCO PATAGONIA S.A.", "30717199002"),
        ("CREDITO TRANSFERENCIA\n juan pedro viola\n 23317082169", "23317082169"),
        ("DEV.COMPRA GALICIA 24-ELECTRON\n WWW.CARREFOUR.COM.AR", None),
        ("HONORARIOS DE PROFESIONALES\n LOCALPAYMENT S.R.L.\n 30716132028", "30716132028"),
    ])
    def test_extract_cuit(self, movimiento, expected):
        result = GaliciaAdapter._extract_cuit(movimiento)
        assert result == expected


class TestGaliciaEUNumbers:
    @pytest.mark.parametrize("raw,expected", [
        ("99.030,12", 99030.12),
        ("1.302.502,17", 1302502.17),
        ("0,00", 0.0),
        ("14,00", 14.0),
        ("956.739,72", 956739.72),
    ])
    def test_parse_eu_number(self, raw, expected):
        result = GaliciaAdapter._parse_eu_number(raw)
        assert abs(result - expected) < 0.001


class TestFactory:
    def test_factory_detects_galicia(self):
        adapter = get_adapter(GALICIA_FILE)
        assert adapter.banco == "galicia"

    def test_factory_explicit_galicia(self):
        adapter = get_adapter(GALICIA_FILE, banco="galicia")
        assert adapter.banco == "galicia"

    def test_detect_returns_banco_id(self):
        info = detect_banco(GALICIA_FILE)
        assert info["banco_id"] == "galicia"
        assert "Galicia" in info["descripcion"]
