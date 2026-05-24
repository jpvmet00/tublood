import streamlit as st
import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.dirname(__file__)))
from style import inject_css
import httpx
import pandas as pd
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")

inject_css()
st.title("Datos Maestros")

# ------------------------------------------------------------------
# 1. Carga de Facturas desde ERP
# ------------------------------------------------------------------
st.header("1. Carga de Facturas desde ERP")
st.caption("Exporta las facturas pendientes desde tu ERP y subelas aqui. La hoja debe llamarse 'pendientes'. Hace upsert: actualiza si ya existe la misma factura.")

libro_file = st.file_uploader("Seleccionar archivo de facturas (.xlsx)", type=["xlsx"], key="libro")
if libro_file and st.button("Subir facturas", type="primary"):
    with st.spinner("Procesando..."):
        resp = httpx.post(
            f"{API_URL}/upload/facturas",
            files={"file": (libro_file.name, libro_file.getvalue(), "application/octet-stream")},
            timeout=60,
        )
    if resp.status_code == 200:
        st.success(f"Facturas procesadas: {resp.json()['facturas_procesadas']}")
        st.rerun()
    else:
        st.error(f"Error {resp.status_code}: {resp.text}")

# Tabla resumen de facturas
resp_f = httpx.get(f"{API_URL}/upload/facturas", timeout=30)
if resp_f.status_code == 200 and resp_f.json():
    facturas = resp_f.json()
    df_f = pd.DataFrame(facturas)

    total = len(df_f)
    vencidas_n = int(df_f["vencida"].sum()) if "vencida" in df_f.columns else 0
    saldo_total = df_f["saldo"].sum()
    con_cuit = int(df_f["cuit"].notna().sum()) if "cuit" in df_f.columns else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total facturas", total)
    col2.metric("Vencidas con saldo", vencidas_n)
    col3.metric("Saldo pendiente", f"$ {saldo_total:,.0f}")
    col4.metric("Con CUIT (conciliables)", con_cuit)

    st.caption("Rojo = vencida con saldo | Verde = cobrada")

    display_cols = [c for c in [
        "nro_factura", "razon_social", "fecha_emision", "condicion_venta",
        "saldo", "fecha_vencimiento", "dias_para_vencer", "vencida", "estado"
    ] if c in df_f.columns]

    df_show = df_f[display_cols].rename(columns={
        "nro_factura":       "Nro Factura",
        "razon_social":      "Razon Social",
        "fecha_emision":     "Fecha Factura",
        "condicion_venta":   "Cond. Pago",
        "saldo":             "Saldo $",
        "fecha_vencimiento": "Vencimiento",
        "dias_para_vencer":  "Dias p/vencer",
        "vencida":           "Vencida",
        "estado":            "Estado",
    })

    def _row_color(row):
        if row.get("Estado") == "cobrado":
            return ["background-color: rgba(27,94,32,0.25)"] * len(row)
        if row.get("Vencida"):
            return ["background-color: rgba(183,28,28,0.25)"] * len(row)
        return [""] * len(row)

    st.dataframe(
        df_show.style.apply(_row_color, axis=1),
        column_config={
            "Saldo $": st.column_config.NumberColumn(format="$ %.0f"),
            "Dias p/vencer": st.column_config.NumberColumn(help="Negativo = ya vencida"),
            "Vencida": st.column_config.CheckboxColumn(disabled=True),
        },
        use_container_width=True,
        hide_index=True,
    )

st.divider()

# ------------------------------------------------------------------
# 2. Padron de Clientes
# ------------------------------------------------------------------
st.header("2. Padron de Clientes")
st.caption(
    "El archivo debe tener columna CUIT. Opcionales: RAZON_SOCIAL, CLIENTE_ID, "
    "MAIL_RECLAMO_FACTURA, MAIL_ATENCION_CLIENTE."
)

padron_file = st.file_uploader("Seleccionar Excel", type=["xlsx", "xls"], key="padron_up")
if padron_file and st.button("Subir y actualizar padron", type="primary"):
    with st.spinner("Procesando..."):
        resp = httpx.post(
            f"{API_URL}/upload/padron",
            files={"file": (padron_file.name, padron_file.getvalue(), "application/octet-stream")},
            timeout=60,
        )
    if resp.status_code == 200:
        data = resp.json()
        col1, col2, col3 = st.columns(3)
        col1.metric("Creados", data["creados"])
        col2.metric("Actualizados", data["actualizados"])
        col3.metric("Total procesados", data["total"])
        st.success("Padron actualizado.")
        st.rerun()
    else:
        st.error(f"Error {resp.status_code}: {resp.text}")

resp_p = httpx.get(f"{API_URL}/upload/padron", timeout=30)
if resp_p.status_code == 200:
    entries = resp_p.json()
    if not entries:
        st.info("El padron esta vacio. Subi un Excel para cargarlo.")
    else:
        df_p = pd.DataFrame(entries)

        col_filter, col_toggle = st.columns([3, 1])
        with col_filter:
            q = st.text_input("Buscar por CUIT o razon social", placeholder="...")
        with col_toggle:
            solo_sin_cliente = st.checkbox("Solo sin cliente ID")

        if q:
            mask = (
                df_p["cuit"].astype(str).str.contains(q, case=False, na=False)
                | df_p["razon_social"].astype(str).str.contains(q, case=False, na=False)
            )
            df_p = df_p[mask]

        if solo_sin_cliente:
            df_p = df_p[df_p["cliente_id"].isna() | (df_p["cliente_id"] == "")]

        # Enriquecer con riesgo crediticio cacheado
        cuits_padron = [c for c in df_p["cuit"].dropna().tolist() if c]
        riesgo_padron = {}
        if cuits_padron:
            try:
                rr = httpx.post(f"{API_URL}/riesgo/bulk", json=cuits_padron, timeout=10)
                if rr.status_code == 200:
                    riesgo_padron = rr.json()
            except Exception:
                pass

        df_p["riesgo_bcra"] = df_p["cuit"].apply(
            lambda c: f"[{riesgo_padron[c]['situacion']}] {riesgo_padron[c]['label']}"
            if c in riesgo_padron else "Sin consultar"
        )

        st.dataframe(df_p, use_container_width=True, hide_index=True)
        st.caption(f"{len(df_p)} entradas mostradas de {len(entries)} totales")

        st.divider()
        st.subheader("Consulta de riesgo crediticio BCRA")
        st.caption("Consulta gratuita al Banco Central. Resultado se cachea 24 horas.")

        col_cuit_q, col_btn_q = st.columns([2, 1])
        with col_cuit_q:
            cuit_buscar = st.text_input("CUIT a consultar", placeholder="30717199020")
        with col_btn_q:
            st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
            consultar_btn = st.button("Consultar BCRA", type="primary")

        if consultar_btn and cuit_buscar.strip():
            with st.spinner("Consultando BCRA..."):
                resp_riesgo = httpx.get(
                    f"{API_URL}/riesgo/{cuit_buscar.strip()}?forzar=true", timeout=15
                )
            if resp_riesgo.status_code == 200:
                r = resp_riesgo.json()
                color_map = {"verde": "success", "amarillo": "warning", "rojo": "error", "gris": "info"}
                fn = getattr(st, color_map.get(r["color"], "info"))
                fn(
                    f"CUIT {r['cuit']} — Situacion {r['situacion']}: **{r['label']}**"
                    + (f" | {r['denominacion']}" if r['denominacion'] else "")
                    + f" | Consultado: {r['fecha_consulta']}"
                )
                if r["alerta"]:
                    st.warning(
                        "Este cliente tiene situacion crediticia irregular en el BCRA. "
                        "Se mostrara una alerta en la seccion de Conciliacion."
                    )
            else:
                st.error(f"Error al consultar: {resp_riesgo.text}")
else:
    st.error(f"No se pudo cargar el padron: {resp_p.status_code}")
