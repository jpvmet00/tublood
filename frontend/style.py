import streamlit as st

TUBLOOD_CSS = """
<style>
/* ── Sidebar ──────────────────────────────────────────── */
[data-testid="stSidebarNav"] a span {
    text-transform: uppercase;
    font-weight: 600;
    letter-spacing: 0.04em;
    font-size: 0.82rem;
}

[data-testid="stSidebarNav"] a[aria-current="page"] span {
    color: #1565C0 !important;
}

[data-testid="stSidebar"] {
    border-right: 2px solid #1565C0;
}

/* ── Metricas ─────────────────────────────────────────── */
[data-testid="metric-container"] {
    background: linear-gradient(135deg, #1565C0 0%, #0288D1 100%);
    border-radius: 10px;
    padding: 12px 16px;
    color: white !important;
}

[data-testid="metric-container"] label,
[data-testid="metric-container"] [data-testid="stMetricValue"],
[data-testid="metric-container"] [data-testid="stMetricDelta"] {
    color: white !important;
}

/* ── Botones primarios ────────────────────────────────── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1565C0 0%, #0288D1 100%);
    border: none;
    color: white;
    font-weight: 600;
    border-radius: 6px;
    transition: opacity 0.2s;
}
.stButton > button[kind="primary"]:hover {
    opacity: 0.88;
}

/* ── Tabla: colores modo claro y oscuro ───────────────── */
/* Fila vencida */
.row-vencida td {
    background-color: rgba(183, 28, 28, 0.25) !important;
}
/* Fila cobrada */
.row-cobrada td {
    background-color: rgba(27, 94, 32, 0.25) !important;
}

/* ── Expander / cards ─────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid #1565C0;
    border-radius: 8px;
}

/* ── Header de pagina ─────────────────────────────────── */
h1 {
    color: #1565C0;
    border-bottom: 2px solid #0288D1;
    padding-bottom: 8px;
}
h2 {
    color: #0288D1;
}
</style>
"""


def inject_css():
    st.markdown(TUBLOOD_CSS, unsafe_allow_html=True)
