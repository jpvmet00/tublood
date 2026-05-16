import re
import pandas as pd
from pathlib import Path
from datetime import date, timedelta
from typing import Dict, List, Optional
from app.adapters.base import BankAdapter
from app.schemas.bank_movement import MovimientoCanonical

# Row indices (0-indexed) in Galicia xlsx
_META_BANCO_ROW = 0     # 'Banco Galicia - Caja Ahorro Pesos'
_META_CUENTA_ROW = 1    # 'Nro. de Cuenta: ...8190105'
_DATA_HEADER_ROW = 5    # 'Fecha | Movimiento | Débito | Crédito | Saldo Parcial | Comentarios'

_GALICIA_SIGNATURE = "Banco Galicia"
_CUIT_LINE_RE = re.compile(r"^\s*(\d{10,11})\s*$")


class GaliciaAdapter(BankAdapter):
    banco = "galicia"

    def validate_file(self, filepath: Path) -> bool:
        if filepath.suffix.lower() not in (".xlsx", ".xls"):
            return False
        try:
            raw = self._read_raw_meta(filepath)
            for row_idx in range(min(3, len(raw))):
                cell = str(raw.iloc[row_idx, 0])
                if _GALICIA_SIGNATURE in cell:
                    return True
            return False
        except Exception:
            return False

    def get_account_info(self, filepath: Path) -> Dict[str, Optional[str]]:
        try:
            raw = self._read_raw_meta(filepath)
            banco_line = str(raw.iloc[_META_BANCO_ROW, 0]).strip()
            cuenta_line = str(raw.iloc[_META_CUENTA_ROW, 0]).strip()
            # "Banco Galicia - Caja Ahorro Pesos"
            tipo = banco_line.replace("Banco Galicia", "").lstrip(" -").strip() or "Caja Ahorro Pesos"
            # "Nro. de Cuenta: ...8190105"
            cuenta = cuenta_line.split(":")[-1].strip() if ":" in cuenta_line else cuenta_line
            return {
                "banco": "Banco Galicia",
                "cuenta": cuenta,
                "tipo": tipo,
                "moneda": "PESOS",
                "descripcion": f"Banco Galicia — {tipo} N° {cuenta}",
            }
        except Exception:
            return {"banco": "Banco Galicia", "cuenta": None, "tipo": None, "moneda": None, "descripcion": "Banco Galicia"}

    def parse(self, filepath: Path) -> List[MovimientoCanonical]:
        df = self._read_data(filepath)
        cutoff = date.today() - timedelta(days=1)
        records: List[MovimientoCanonical] = []

        for _, row in df.iterrows():
            fecha = row.get("fecha")
            if not isinstance(fecha, date):
                continue
            if fecha > cutoff:
                continue

            # Galicia: use Credito column (inbound payments only)
            credito = self._parse_eu_number(str(row.get("credito", "0")))
            if credito <= 0:
                continue

            movimiento = str(row.get("movimiento", ""))
            cuit = self._extract_cuit(movimiento)
            razon = self._extract_razon(movimiento)

            records.append(
                MovimientoCanonical(
                    fecha=fecha,
                    concepto=movimiento.replace("\n", " ").strip(),
                    importe=credito,
                    cuit_extraido=cuit,
                    razon_social=razon,
                    banco=self.banco,
                    referencia=None,
                )
            )
        return records

    # ------------------------------------------------------------------

    def _read_raw_meta(self, filepath: Path) -> pd.DataFrame:
        # header=None so iloc[N] == file row N exactly
        return pd.read_excel(filepath, header=None, engine="openpyxl", nrows=6)

    def _read_data(self, filepath: Path) -> pd.DataFrame:
        df = pd.read_excel(filepath, header=_DATA_HEADER_ROW, engine="openpyxl")
        df.columns = [str(c).strip().lower().replace("é", "e").replace("ó", "o") for c in df.columns]

        rename = {
            "fecha": "fecha",
            "movimiento": "movimiento",
            "debito": "debito",
            "credito": "credito",
            "saldo parcial": "saldo_parcial",
            "comentarios": "comentarios",
        }
        df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

        if "fecha" in df.columns:
            df["fecha"] = pd.to_datetime(df["fecha"], dayfirst=True, errors="coerce").dt.date

        return df

    @staticmethod
    def _parse_eu_number(value: str) -> float:
        """Convert European-format number string '1.234,56' to float 1234.56."""
        clean = value.strip().replace(".", "").replace(",", ".")
        try:
            return float(clean)
        except ValueError:
            return 0.0

    @staticmethod
    def _extract_cuit(movimiento: str) -> Optional[str]:
        """Find a CUIT in the multiline Movimiento field.

        Galicia puts the CUIT on its own line: line that contains only 10-11 digits.
        """
        for line in movimiento.split("\n"):
            m = _CUIT_LINE_RE.match(line)
            if m:
                return m.group(1)
        return None

    @staticmethod
    def _extract_razon(movimiento: str) -> Optional[str]:
        """Extract company name from Galicia movimiento.

        Format:
          Line 0: tipo (CREDITO TRANSFERENCIA / TRANSFERENCIAS CASH PROVEEDORES)
          Line 1: razon social
          Line 2: CUIT (digits only)
        """
        lines = [l.strip() for l in movimiento.split("\n") if l.strip()]
        if len(lines) >= 2:
            candidate = lines[1]
            # Skip if it looks like a CUIT or a bank name
            if not _CUIT_LINE_RE.match(candidate) and len(candidate) > 3:
                return candidate
        return None
