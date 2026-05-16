import streamlit as st

st.set_page_config(page_title="TUBLOOD - Conciliacion", layout="wide")

pages = {
    "Subir archivos": "pages/01_upload.py",
    "Dashboard": "pages/02_dashboard.py",
}

st.sidebar.title("TUBLOOD")
st.sidebar.markdown("Sistema de conciliacion de cobros")
st.sidebar.markdown("---")
st.sidebar.markdown("Navegacion via menu de paginas.")
