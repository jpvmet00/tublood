import streamlit as st
import httpx
import pandas as pd
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.title("Cargar archivos")

# ------------------------------------------------------------------
# Extracto del banco
# ------------------------------------------------------------------
st.header("Extracto del banco")
st.caption("Soportado: Banco Macro (.xls/.xlsx) y Banco Galicia (.xlsx). Podés subir los dos a la vez.")

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
