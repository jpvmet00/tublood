from pathlib import Path
from app.db.models import MovimientoBanco, Factura

FIXTURES = Path(__file__).parent.parent / "fixtures"
MACRO_FILE = FIXTURES / "movimientos_macro_test.xlsx"
GALICIA_FILE = FIXTURES / "movimientos_galicia_test.xlsx"
LIBRO3 = FIXTURES / "Libro3_test.xlsx"


class TestHealth:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestDetectBanco:
    def test_detect_macro(self, client):
        with open(MACRO_FILE, "rb") as f:
            resp = client.post("/upload/banco/detect", files={"file": ("mov.xlsx", f, "application/octet-stream")})
        assert resp.status_code == 200
        body = resp.json()
        assert body["banco_id"] == "macro"
        assert "Macro" in body["descripcion"]
        assert body["cuenta"] == "451806976969666"

    def test_detect_galicia(self, client):
        with open(GALICIA_FILE, "rb") as f:
            resp = client.post("/upload/banco/detect", files={"file": ("mov.xlsx", f, "application/octet-stream")})
        assert resp.status_code == 200
        body = resp.json()
        assert body["banco_id"] == "galicia"
        assert "Galicia" in body["descripcion"]
        assert "8190105" in body["cuenta"]

    def test_detect_unknown_returns_400(self, client, tmp_path):
        bad = tmp_path / "desconocido.xlsx"
        bad.write_bytes(b"this is not an excel file")
        with open(bad, "rb") as f:
            resp = client.post("/upload/banco/detect", files={"file": ("bad.xlsx", f, "application/octet-stream")})
        assert resp.status_code == 400


class TestUploadBanco:
    def test_upload_macro_ok(self, client, db):
        with open(MACRO_FILE, "rb") as f:
            resp = client.post(
                "/upload/banco",
                files={"file": ("movimientos.xlsx", f, "application/octet-stream")},
                data={"banco": "macro"},
            )
        assert resp.status_code == 200
        assert resp.json()["movimientos_insertados"] == 4

    def test_upload_galicia_ok(self, client, db):
        with open(GALICIA_FILE, "rb") as f:
            resp = client.post(
                "/upload/banco",
                files={"file": ("galicia.xlsx", f, "application/octet-stream")},
                data={"banco": "galicia"},
            )
        assert resp.status_code == 200
        assert resp.json()["movimientos_insertados"] == 4

    def test_upload_macro_idempotente(self, client, db):
        for _ in range(2):
            with open(MACRO_FILE, "rb") as f:
                resp = client.post(
                    "/upload/banco",
                    files={"file": ("mov.xlsx", f, "application/octet-stream")},
                    data={"banco": "macro"},
                )
        assert resp.json()["movimientos_insertados"] == 0

    def test_upload_facturas_ok(self, client, db):
        with open(LIBRO3, "rb") as f:
            resp = client.post(
                "/upload/facturas",
                files={"file": ("Libro3.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            )
        assert resp.status_code == 200
        assert resp.json()["facturas_procesadas"] == 6


class TestConciliacionRoutes:
    def _seed(self, db):
        from app.services.ingestion import cargar_facturas, cargar_padron
        from app.services.conciliation import ingestar_movimientos, conciliar_banco
        cargar_facturas(db, filepath=LIBRO3)
        cargar_padron(db)
        ingestar_movimientos(db, MACRO_FILE, banco="macro")
        ingestar_movimientos(db, GALICIA_FILE, banco="galicia")
        conciliar_banco(db)

    def test_vencidas_returns_list(self, client, db):
        from app.services.ingestion import cargar_facturas
        cargar_facturas(db, filepath=LIBRO3)
        resp = client.get("/conciliacion/vencidas")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_resumen_structure(self, client, db):
        resp = client.get("/conciliacion/resumen")
        assert resp.status_code == 200
        for key in ("total_facturas", "con_saldo_pendiente", "cobradas", "vencidas", "saldo_total"):
            assert key in resp.json()

    def test_historial_returns_list(self, client, db):
        self._seed(db)
        resp = client.get("/conciliacion/historial")
        assert resp.status_code == 200
        assert len(resp.json()) > 0
