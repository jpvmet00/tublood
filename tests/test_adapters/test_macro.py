import pytest
from pathlib import Path
from datetime import date
from app.adapters.macro import MacroAdapter
from app.adapters.factory import get_adapter, detect_banco

FIXTURES = Path(__file__).parent.parent / "fixtures"
MACRO_FILE = FIXTURES / "movimientos_macro_test.xlsx"


class TestMacroAdapterValidation:
    def test_validates_correct_file(self):
        assert MacroAdapter().validate_file(MACRO_FILE) is True

    def test_rejects_nonexistent_file(self):
        assert MacroAdapter().validate_file(Path("/tmp/no_existe.xls")) is False

    def test_rejects_wrong_extension(self):
        assert MacroAdapter().validate_file(Path("/tmp/file.csv")) is False

    def test_rejects_galicia_file(self):
        galicia_file = FIXTURES / "movimientos_galicia_test.xlsx"
        assert MacroAdapter().validate_file(galicia_file) is False


class TestMacroAccountInfo:
    def test_banco_name(self):
        info = MacroAdapter().get_account_info(MACRO_FILE)
        assert info["banco"] == "Banco Macro"

    def test_cuenta_number(self):
        info = MacroAdapter().get_account_info(MACRO_FILE)
        assert info["cuenta"] == "451806976969666"

    def test_tipo(self):
        info = MacroAdapter().get_account_info(MACRO_FILE)
        assert info["tipo"] == "Caja de Ahorro"

    def test_moneda(self):
        info = MacroAdapter().get_account_info(MACRO_FILE)
        assert info["moneda"] == "PESOS"

    def test_descripcion_contains_key_info(self):
        info = MacroAdapter().get_account_info(MACRO_FILE)
        assert "Macro" in info["descripcion"]
        assert "451806976969666" in info["descripcion"]


class TestMacroAdapterParse:
    def test_only_credits_returned(self):
        movs = MacroAdapter().parse(MACRO_FILE)
        # Fixture has 1 debit (-100000) that must be excluded
        assert all(m.importe > 0 for m in movs)

    def test_returns_correct_count(self):
        movs = MacroAdapter().parse(MACRO_FILE)
        # 3 valid credits + 1 without CUIT = 4 total (debit excluded)
        assert len(movs) == 4

    def test_extracts_cuit_from_concepto(self):
        movs = MacroAdapter().parse(MACRO_FILE)
        cuits = {m.cuit_extraido for m in movs if m.cuit_extraido}
        assert "27218826488" in cuits
        assert "20373127338" in cuits
        assert "20394088324" in cuits

    def test_row_without_cuit_has_none(self):
        movs = MacroAdapter().parse(MACRO_FILE)
        no_cuit = [m for m in movs if m.cuit_extraido is None]
        assert len(no_cuit) == 1

    def test_banco_field(self):
        movs = MacroAdapter().parse(MACRO_FILE)
        assert all(m.banco == "macro" for m in movs)

    def test_importes_positive(self):
        movs = MacroAdapter().parse(MACRO_FILE)
        assert all(m.importe > 0 for m in movs)

    def test_fecha_is_date(self):
        movs = MacroAdapter().parse(MACRO_FILE)
        assert all(isinstance(m.fecha, date) for m in movs)


class TestMacroAdapterCuitExtraction:
    @pytest.mark.parametrize("concepto,expected", [
        ("TRANSF:L18MKX9RXY8Z1KV49O6WYV-27218826488", "27218826488"),
        ("TRANSF:OTRO-20111222333", "20111222333"),
        ("DEBITO AUTOMATICO", None),
        ("TRANSF:SINCUIT-", None),
        ("TRANSF:REF-1234567890", "1234567890"),
    ])
    def test_cuit_regex(self, concepto, expected):
        result = MacroAdapter._extract_cuit(concepto)
        assert result == expected


class TestFactory:
    def test_factory_detects_macro_by_content(self):
        adapter = get_adapter(MACRO_FILE)
        assert adapter.banco == "macro"

    def test_factory_explicit_banco(self):
        adapter = get_adapter(MACRO_FILE, banco="macro")
        assert adapter.banco == "macro"

    def test_detect_returns_banco_id(self):
        info = detect_banco(MACRO_FILE)
        assert info["banco_id"] == "macro"
        assert "Macro" in info["descripcion"]

    def test_factory_raises_on_unknown(self, tmp_path):
        bad = tmp_path / "unknown.xlsx"
        bad.write_bytes(b"not a valid excel file at all")
        with pytest.raises(ValueError, match="No hay adaptador"):
            get_adapter(bad)
