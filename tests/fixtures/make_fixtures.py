"""Run once to generate test fixture files.

Libro3_test.xlsx  — facturas con CUITs de AMBOS bancos
  Macro credits used:
    CUIT 27218826488  $4,400     -> factura saldo $4,400  (match exacto)
    CUIT 20373127338  $14,000    -> factura saldo $14,500  (dentro 10%)
    CUIT 20394088324  $20,000    -> factura saldo $20,000  (match exacto)
  Galicia credits used:
    CUIT 30717199002  $99,030.12 -> factura saldo $100,000 (dentro 10%)
    CUIT 30717199002  $23,146.62 -> factura saldo $23,000  (dentro 10%)
    CUIT 30716132028  $14        -> factura saldo $14      (match exacto, monto chico)

movimientos_macro_test.xlsx — extracto Macro sintetico (positivos = creditos)
movimientos_galicia_test.xlsx — extracto Galicia sintetico (col Credito)
"""
import pandas as pd
from pathlib import Path

HERE = Path(__file__).parent


def make_libro3():
    pendientes = pd.DataFrame({
        "NRO": ["F-MAC-001", "F-MAC-002", "F-MAC-003", "F-GAL-001", "F-GAL-002", "F-GAL-003"],
        "CLIENTE": ["CLI-MACRO-A", "CLI-MACRO-B", "CLI-MACRO-C",
                    "INSTITUTO DATA SCIENCE", "INSTITUTO DATA SCIENCE", "LOCALPAYMENT"],
        "CUIT": ["27218826488", "20373127338", "20394088324",
                 "30717199002", "30717199002", "30716132028"],
        "IMPORTE": [4400, 14500, 20000, 100000, 23000, 14],
        "SALDO":   [4400, 14500, 20000, 100000, 23000, 14],
        "FECHA":        ["2026-01-10", "2026-01-15", "2026-01-20",
                         "2026-02-01", "2026-02-15", "2026-03-01"],
        "VENCIMIENTO":  ["2026-02-09", "2026-02-14", "2026-02-19",
                         "2026-03-03", "2026-03-17", "2026-03-31"],
        "CONDICION": ["30d", "30d", "30d", "30d", "30d", "30d"],
        "VENDEDOR":  ["Carlos", "Carlos", "Maria", "Ana", "Ana", "Pedro"],
        "EMAIL":     ["carlos@tb.com", "carlos@tb.com", "maria@tb.com",
                      "ana@tb.com", "ana@tb.com", "pedro@tb.com"],
    })
    cobranzas = pd.DataFrame({
        "NRO": [],
        "CLIENTE": [],
        "IMPORTE": [],
        "FECHA": [],
    })
    with pd.ExcelWriter(HERE / "Libro3_test.xlsx") as w:
        pendientes.to_excel(w, sheet_name="pendientes", index=False)
        cobranzas.to_excel(w, sheet_name="cobranzas", index=False)
    print("Created Libro3_test.xlsx (6 facturas, CUITs Macro + Galicia)")


def make_macro():
    """Synthetic Macro XLS that matches the real file structure."""
    meta = pd.DataFrame({
        "col0": ["Últimos Movimientos", None, "CUENTA CORRIENTE ESPECIAL EN PESOS",
                 None, "Tipo", "Número", "Moneda", "Fecha"],
        "col1": [None] * 8,
        "col2": [None, None, None, None, "Caja de Ahorro", "451806976969666", "PESOS", None],
        "col3": [None, None, None, None, None, None, None, "Nro. de Referencia"],
        "col4": [None, None, None, None, None, None, None, "Causal"],
        "col5": [None, None, None, None, None, None, None, "Concepto"],
        "col6": [None, None, None, None, None, None, None, "Importe"],
        "col7": [None] * 8,
        "col8": [None] * 8,
        "col9": [None] * 8,
        "col10": [None, None, None, None, None, None, None, "Saldo"],
    })
    # Data rows (matching real format)
    data_rows = [
        # fecha, _, _, referencia, causal, concepto, importe, _, _, _, saldo
        ["2026-04-14", None, None, "478150", "4093", "TRANSF:L18MKX9RXY8Z1KV49O6WYV-27218826488", 4400, None, None, None, 348728320.06],
        ["2026-04-14", None, None, "139940", "4093", "TRANSF:LOEJWV9JZEPR00ZR2QMD0G-20373127338", 14000, None, None, None, 348723920.06],
        ["2026-04-14", None, None, "900365", "4093", "TRANSF:LOEJWV9JZEPRYV432QMD0G-20394088324", 20000, None, None, None, 348796420.06],
        ["2026-04-14", None, None, "787915", "4083", "TRANSF:Z6OLMDN3VDKPM0YK2E7RQ5-", -100000, None, None, None, 348706420.06],  # debito, debe ignorarse
        ["2026-04-15", None, None, "123456", "4093", "TRANSF:SINREFCUIT0000000000000", 5000, None, None, None, 348801420.06],   # sin CUIT al final
    ]
    for row in data_rows:
        row_dict = {f"col{i}": v for i, v in enumerate(row)}
        meta = pd.concat([meta, pd.DataFrame([row_dict])], ignore_index=True)

    # Write without index/header so row positions are exactly as in real file
    meta.to_excel(HERE / "movimientos_macro_test.xls", index=False, header=False, engine="xlwt" if False else None)
    # xlwt not available for Python 3.9+; use openpyxl with .xlsx
    meta.to_excel(HERE / "movimientos_macro_test.xlsx", index=False, header=False, engine="openpyxl")
    print("Created movimientos_macro_test.xlsx")


def make_galicia():
    """Synthetic Galicia XLSX matching real file structure (header at row 5)."""
    meta_rows = [
        ["Banco Galicia - Caja Ahorro Pesos", None, None, None, None, None],
        ["Nro. de Cuenta: ...8190105", None, None, None, None, None],
        ["Fecha Actual: 15/5/2026", None, None, None, None, None],
        ["Hora Actual: 21:31", None, None, None, None, None],
        ["Intervalo de Consulta: del 01/04/2026 al 18/05/2026", None, None, None, None, None],
        ["Fecha", "Movimiento", "Debito", "Credito", "Saldo Parcial", "Comentarios"],
        # Data rows: Fecha DD/MM/YYYY, Movimiento multiline, Debito, Credito, Saldo, Comentarios
        ["05/05/2026", "TRANSFERENCIAS CASH PROVEEDORES\n INSTITUTO DATA SCIENCE S.A.\n 30717199002\n BANCO PATAGONIA S.A.", "0,00", "99.030,12", "500000,00", None],
        ["17/04/2026", "TRANSFERENCIAS CASH PROVEEDORES\n INSTITUTO DATA SCIENCE S.A.\n 30717199002\n BANCO PATAGONIA S.A.", "0,00", "23.146,62", "400000,00", None],
        ["06/05/2026", "HONORARIOS DE PROFESIONALES\n LOCALPAYMENT S.R.L.\n 30716132028", "0,00", "14,00", "300000,00", None],
        ["15/05/2026", "TRANSFERENCIA A TERCEROS\n JOSE LAUTARO ASSMANN\n 20375637635\n VARIOS\n MERCADO LIBRE SRL", "-50.500,00", "0,00", "610766,23", None],  # debito, ignora
        ["08/05/2026", "CREDITO TRANSFERENCIA\n juan pedro viola\n 23317082169", "0,00", "956.739,72", "200000,00", None],  # transferencia propia
    ]
    df = pd.DataFrame(meta_rows)
    df.to_excel(HERE / "movimientos_galicia_test.xlsx", index=False, header=False, engine="openpyxl")
    print("Created movimientos_galicia_test.xlsx")


if __name__ == "__main__":
    make_libro3()
    make_macro()
    make_galicia()
