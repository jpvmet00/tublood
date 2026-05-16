import streamlit as st
import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.dirname(__file__)))
from style import inject_css
import httpx
import pandas as pd
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")

inject_css()
st.title("Cargar archivos")

# ------------------------------------------------------------------
# Pre-validacion: verificar padron y facturas antes de procesar banco
# ------------------------------------------------------------------
_padron_ok = False
_facturas_ok = False

try:
    _rp = httpx.get(f"{API_URL}/upload/padron", timeout=10)
    _padron_ok = _rp.status_code == 200 and bool(_rp.json())
except Exception:
    pass

try:
    _rf = httpx.get(f"{API_URL}/upload/facturas", timeout=10)
    _facturas_ok = _rf.status_code == 200 and bool(_rf.json())
except Exception:
    pass

if not _padron_ok or not _facturas_ok:
    st.warning("Antes de procesar extractos del banco, asegurate de haber cargado:")
    col_ch1, col_ch2 = st.columns(2)
    with col_ch1:
        st.markdown(f"{'[x]' if _padron_ok else '[ ]'} **Padron de clientes** (Datos Maestros)")
    with col_ch2:
        st.markdown(f"{'[x]' if _facturas_ok else '[ ]'} **Facturas pendientes** (Libro3 en Datos Maestros)")
    if not _padron_ok:
        st.error("Sin padron no es posible conciliar: los movimientos no se pueden vincular a clientes.")

st.divider()

# ------------------------------------------------------------------
# Extracto del banco
# ------------------------------------------------------------------
st.header("Extracto del banco")
st.caption("Soportado: Banco Macro (.xls/.xlsx) y Banco Galicia (.xlsx). Podes subir los dos a la vez.")

banco_files = st.file_uploader(
    "Seleccionar archivos del banco",
    type=["xls", "xlsx"],
    accept_multiple_files=True,
    key="banco",
)

if banco_files:
    detecciones = []
    errores_detect = []

    for f in banco_files:
        file_bytes = f.getvalue()
        resp = httpx.post(
            f"{API_URL}/upload/banco/detect",
            files={"file": (f.name, file_bytes, "application/octet-stream")},
            timeout=30,
        )
        if resp.status_code == 200:
            info = resp.json()
            info["_filename"] = f.name
            info["_bytes"] = file_bytes
            detecciones.append(info)
        else:
            errores_detect.append(f"{f.name}: {resp.json().get('detail', resp.text)}")

    if errores_detect:
        for e in errores_detect:
            st.error(f"No se pudo identificar: {e}")

    if detecciones:
        st.subheader("Bancos detectados")
        for d in detecciones:
            st.info(f"**{d['_filename']}** -> {d['descripcion']}")

        if st.button("Confirmar y procesar todos", type="primary"):
            with st.spinner("Procesando todos los extractos..."):
                files_payload = [
                    ("files", (d["_filename"], d["_bytes"], "application/octet-stream"))
                    for d in detecciones
                ]
                resp = httpx.post(
                    f"{API_URL}/upload/banco/multi",
                    files=files_payload,
                    timeout=600,
                )

            if resp.status_code == 200:
                data = resp.json()

                for arch in data["archivos_procesados"]:
                    rango = ""
                    if arch.get("fecha_desde") and arch.get("fecha_hasta"):
                        rango = f" | Movimientos: {arch['fecha_desde']} a {arch['fecha_hasta']}"

                    if arch.get("ya_procesado"):
                        st.warning(
                            f"{arch['archivo']} ({arch['banco']}): "
                            f"archivo ya procesado anteriormente, no se insertaron movimientos nuevos.{rango}"
                        )
                    else:
                        st.success(
                            f"{arch['archivo']} ({arch['banco']}): "
                            f"{arch['movimientos_insertados']} movimientos nuevos.{rango}"
                        )

                for err in data.get("errores", []):
                    st.warning(f"{err['archivo']}: {err['error']}")

                st.metric("Total movimientos nuevos", data["movimientos_insertados_total"])
                st.metric("Conciliaciones generadas", data["conciliaciones_generadas"])

                if data["detalle"]:
                    df = pd.DataFrame(data["detalle"])
                    st.dataframe(df, use_container_width=True)
            else:
                st.error(f"Error {resp.status_code}: {resp.text}")
