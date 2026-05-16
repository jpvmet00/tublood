import streamlit as st
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from style import inject_css

st.set_page_config(
    page_title="TUBLOOD - Conciliacion",
    page_icon="T",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# ── Header ────────────────────────────────────────────────────────────────────
col_logo, col_titulo = st.columns([1, 5])
with col_logo:
    st.markdown(
        "<div style='font-size:3rem;font-weight:900;color:#1565C0;margin-top:8px'>TB</div>",
        unsafe_allow_html=True,
    )
with col_titulo:
    st.markdown(
        "<h1 style='margin-bottom:0'>TUBLOOD — Sistema de Conciliacion de Cobros</h1>"
        "<p style='color:#555;margin-top:4px'>Automatizacion de cobranzas, conciliacion bancaria y gestion de reclamos</p>",
        unsafe_allow_html=True,
    )

st.divider()

# ── Que hace la plataforma ─────────────────────────────────────────────────────
st.markdown("## Como funciona")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown("### 1. Cargas el Libro3")
    st.markdown(
        "Subi el archivo de facturas pendientes. "
        "El sistema carga automaticamente los saldos, fechas de vencimiento "
        "y condiciones de pago de cada cliente."
    )
with c2:
    st.markdown("### 2. Cargas el padron")
    st.markdown(
        "Vincula cada CUIT con su cliente interno. "
        "Soporta emails de contacto para reclamos y atencion al cliente. "
        "Se actualiza de forma incremental."
    )
with c3:
    st.markdown("### 3. Subes los extractos")
    st.markdown(
        "Arrastra los archivos del home banking de Banco Macro y/o Banco Galicia. "
        "El sistema detecta el banco automaticamente y concilia los creditos "
        "contra las facturas pendientes por CUIT."
    )
with c4:
    st.markdown("### 4. Gestionas reclamos")
    st.markdown(
        "Facturas vencidas sin pago generan reclamos. "
        "El historial de respuestas queda registrado. "
        "Un agente de IA analiza el contexto y genera un borrador de mail "
        "o un plan de accion."
    )

st.divider()

# ── Estado actual del sistema ──────────────────────────────────────────────────
st.markdown("## Estado del sistema")

import httpx, os
API_URL = os.getenv("API_URL", "http://localhost:8000")

try:
    resp = httpx.get(f"{API_URL}/conciliacion/resumen", timeout=5)
    if resp.status_code == 200:
        r = resp.json()
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Facturas cargadas", r["total_facturas"])
        col2.metric("Con saldo pendiente", r["con_saldo_pendiente"])
        col3.metric("Cobradas", r["cobradas"])
        col4.metric("Vencidas", r["vencidas"])
        col5.metric("Reclamos abiertos", r.get("reclamos_abiertos", 0))

        if r["total_facturas"] == 0:
            st.info("Para empezar: ve a Datos Maestros y carga el padron de clientes y el Libro3 con las facturas pendientes.")
        elif r["vencidas"] > 0:
            st.warning(f"Hay {r['vencidas']} factura(s) vencida(s) con saldo pendiente. Revisa el Dashboard.")
        else:
            st.success("Sistema al dia. Sin facturas vencidas pendientes.")
    else:
        st.error("API no disponible. Asegurate de que el backend este corriendo.")
except Exception:
    st.error("No se puede conectar con la API en http://localhost:8000. Ejecuta: python -m uvicorn app.main:app --port 8000 --reload")

st.divider()

# ── Orden recomendado de carga ─────────────────────────────────────────────────
st.markdown("## Orden de carga recomendado")

st.markdown("""
| Paso | Archivo | Donde | Por que primero |
|------|---------|-------|-----------------|
| 1 | `padron_clientes.xlsx` | Datos Maestros | Vincula CUIT con cliente ID antes de procesar facturas y movimientos |
| 2 | `Libro3.xlsx` | Datos Maestros | Carga las facturas pendientes con sus saldos |
| 3 | Extractos del banco | Cargar archivos | Concilia los creditos bancarios contra las facturas ya cargadas |
| 4 | `reclamos_demo.xlsx` | Reclamos | Opcional — carga historial de reclamos existentes |
""")

st.divider()

# ── Bancos soportados ──────────────────────────────────────────────────────────
st.markdown("## Bancos soportados")
col_a, col_b, col_c = st.columns([1, 1, 2])
with col_a:
    st.markdown(
        "<div style='border:1px solid #1565C0;border-radius:8px;padding:16px;text-align:center'>"
        "<div style='font-size:1.5rem;font-weight:700;color:#1565C0'>Banco Macro</div>"
        "<div style='color:#666;font-size:0.85rem;margin-top:8px'>Formato .xls / .xlsx<br>Deteccion automatica<br>Extrae CUIT del concepto</div>"
        "</div>",
        unsafe_allow_html=True,
    )
with col_b:
    st.markdown(
        "<div style='border:1px solid #0288D1;border-radius:8px;padding:16px;text-align:center'>"
        "<div style='font-size:1.5rem;font-weight:700;color:#0288D1'>Banco Galicia</div>"
        "<div style='color:#666;font-size:0.85rem;margin-top:8px'>Formato .xlsx<br>Deteccion automatica<br>Extrae CUIT y razon social</div>"
        "</div>",
        unsafe_allow_html=True,
    )
with col_c:
    st.markdown(
        "<div style='border:1px solid #ccc;border-radius:8px;padding:16px'>"
        "<div style='font-weight:700;color:#333'>Logica de conciliacion</div>"
        "<div style='color:#666;font-size:0.85rem;margin-top:8px'>"
        "Cada credito bancario se matchea contra facturas pendientes del mismo CUIT "
        "ordenadas por vencimiento (FIFO). Tolerancia configurable (default 10%). "
        "Un credito puede cubrir multiples facturas. El saldo se actualiza en tiempo real."
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )
