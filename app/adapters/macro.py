import re
import pandas as pd
from pathlib import Path
from datetime import date, timedelta
from typing import Dict, List, Optional
from app.adapters.base import BankAdapter
from app.schemas.bank_movement import MovimientoCanonical

# CONCEPTO format: "TRANSF:ALPHANUM-27218826488"
_CUIT_RE = re.compile(r"-(\d{10,11})$")

# Row indices with header=None (0-indexed, file rows as-is)
_META_TIPO_ROW = 4      # 'Tipo', _, 'Caja de Ahorro'
_META_NUMERO_ROW = 5    # 'Número', _, 451806976969666
_META_MONEDA_ROW = 6    # 'Moneda', _, 'PESOS'
_DATA_HEADER_ROW = 7    # 'Fecha', _, _, 'Nro. de Referencia', 'Causal', 'Concepto', 'Importe', ..., 'Saldo'

# Distinctive string in cell (0,0) of every Macro export
_MACRO_SIGNATURE = "Últimos Movimientos"


class MacroAdapter(BankAdapter):
    banco = "macro"

    def validate_file(self, filepath: Path) -> bool:
        suffix = filepath.suffix.lower()
        if suffix not in (".xls", ".xlsx"):
            return False
        try:
            raw = self._read_raw_meta(filepath)
            # Row 0 of the file has 'Últimos Movimientos' in col 0
            cell = str(raw.iloc[0, 0])
            return _MACRO_SIGNATURE in cell
        except Exception:
            return False

    def get_account_info(self, filepath: Path) -> Dict[str, Optional[str]]:
        try:
            raw = self._read_raw_meta(filepath)
            tipo = str(raw.iloc[_META_TIPO_ROW, 2]).strip()
            numero = str(raw.iloc[_META_NUMERO_ROW, 2]).strip()
            moneda = str(raw.iloc[_META_MONEDA_ROW, 2]).strip()
            # numero comes out as float (e.g. 4.51806976969666e+14), normalize
            try:
                numero = str(int(float(numero)))
            except Exception:
                pass
            return {
                "banco": "Banco Macro",
                "cuenta": numero,
                "tipo": tipo,
                "moneda": moneda,
                "descripcion": f"Banco Macro — {tipo} {moneda} N° {numero}",
            }
        except Exception:
            return {"banco": "Banco Macro", "cuenta": None, "tipo": None, "moneda": None, "descripcion": "Banco Macro"}

    def parse(self, filepath: Path) -> List[MovimientoCanonical]:
        df = self._read_data(filepath)
        cutoff = date.today() - timedelta(days=1)
        records: List[MovimientoCanonical] = []

        for _, row in df.iterrows():
            fecha = row.get("fecha")
            try:
                if pd.isnull(fecha):
                    continue
            except (TypeError, ValueError):
                pass
            if not isinstance(fecha, date):
                continue
            if fecha > cutoff:
                continue

            importe = row.get("importe", 0)
            try:
                importe = float(importe)
            except (TypeError, ValueError):
                continue
            if importe <= 0:
                continue

            concepto = str(row.get("concepto", ""))
            cuit = self._extract_cuit(concepto)

            records.append(
                MovimientoCanonical(
                    fecha=fecha,
                    concepto=concepto,
                    importe=importe,
                    cuit_extraido=cuit,
                    banco=self.banco,
                    referencia=str(row.get("referencia", "")) or None,
                )
            )
        return records

    # ------------------------------------------------------------------

    def _read_raw_meta(self, filepath: Path) -> pd.DataFrame:
        engine = "xlrd" if filepath.suffix.lower() == ".xls" else "openpyxl"
        # header=None so iloc[N] == file row N exactly
        return pd.read_excel(filepath, header=None, engine=engine, nrows=10)

    def _read_data(self, filepath: Path) -> pd.DataFrame:
        engine = "xlrd" if filepath.suffix.lower() == ".xls" else "openpyxl"
        df = pd.read_excel(filepath, header=_DATA_HEADER_ROW, engine=engine)
        df.columns = [str(c).strip().upper() for c in df.columns]

        rename = {
            "FECHA": "fecha",
            "NRO. DE REFERENCIA": "referencia",
            "CAUSAL": "causal",
            "CONCEPTO": "concepto",
            "IMPORTE": "importe",
            "SALDO": "saldo",
        }
        df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

        if "fecha" in df.columns:
            df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce").dt.date
        if "importe" in df.columns:
            df["importe"] = pd.to_numeric(df["importe"], errors="coerce")

        return df

    @staticmethod
    def _extract_cuit(concepto: str) -> Optional[str]:
        m = _CUIT_RE.search(concepto.strip())
        return m.group(1) if m else None
