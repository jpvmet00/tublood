import streamlit as st
import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.dirname(__file__)))
from style import inject_css
import httpx
import pandas as pd
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")

inject_css()
_dialog = getattr(st, "dialog", getattr(st, "experimental_dialog", None))


def _get(path, **kw):
    return httpx.get(f"{API_URL}{path}", timeout=15, **kw)


def _post(path, **kw):
    return httpx.post(f"{API_URL}{path}", timeout=60, **kw)


st.title("Reclamos de clientes")

# ------------------------------------------------------------------
# Upload
# ------------------------------------------------------------------
with st.expander("Cargar reclamos desde Excel"):
    st.caption("Columnas: CLIENTE_ID, CUIT, DESCRIPCION, ULTIMA_RTA_AL_CLIENTE, HISTORICO_RESPUESTAS (sep. |||), COMO_SE_RESOLVIO, ACTIVO, FECHA_INICIO, FECHA_CIERRE")
    rec_file = st.file_uploader("Seleccionar Excel", type=["xlsx", "xls"], key="rec_up")
    if rec_file and st.button("Subir reclamos"):
        resp = _post(
            "/upload/reclamos",
            files={"file": (rec_file.name, rec_file.getvalue(), "application/octet-stream")},
        )
        if resp.status_code == 200:
            d = resp.json()
            st.success(f"Creados: {d['creados']} | Actualizados: {d['actualizados']} | Total: {d['total']}")
            st.rerun()
        else:
            st.error(f"Error {resp.status_code}: {resp.text}")

st.divider()

# ------------------------------------------------------------------
# Filtros
# ------------------------------------------------------------------
col_f1, col_f2 = st.columns([2, 1])
with col_f1:
    buscar = st.text_input("Buscar por cliente o descripcion", placeholder="...")
with col_f2:
    solo_activos = st.checkbox("Solo reclamos abiertos", value=True)

params = "?solo_activos=true" if solo_activos else ""
resp = _get(f"/reclamos{params}")
if resp.status_code != 200:
    st.error(f"No se pudo cargar reclamos: {resp.text}")
    st.stop()

reclamos = resp.json()

if buscar:
    reclamos = [
        r for r in reclamos
        if buscar.lower() in (r.get("cliente_id") or "").lower()
        or buscar.lower() in (r.get("descripcion") or "").lower()
    ]

if not reclamos:
    st.info("No hay reclamos con los filtros actuales.")
    st.stop()


# ------------------------------------------------------------------
# Dialogs
# ------------------------------------------------------------------
@_dialog("Historial del reclamo", width="large")
def modal_historial(reclamo: dict):
    st.subheader(f"Cliente {reclamo['cliente_id']} — {reclamo.get('cuit', '')}")
    st.write(f"**Descripcion:** {reclamo['descripcion']}")
    st.write(f"**Inicio:** {reclamo['fecha_inicio']}  |  **Cierre:** {reclamo.get('fecha_cierre') or 'abierto'}")
    st.write(f"**Estado:** {'Abierto' if reclamo['activo'] else 'Cerrado'}")
    if reclamo.get("como_se_resolvio"):
        st.success(f"Resolucion: {reclamo['como_se_resolvio']}")
    st.divider()
    st.subheader("Historial de respuestas")
    historico = reclamo.get("historico") or []
    if not historico:
        st.info("Sin entradas en el historial.")
    else:
        for entrada in historico:
            st.markdown(f"**{entrada['fecha']}** — {entrada['texto']}")
    st.divider()
    st.write(f"**Ultima respuesta:** {reclamo.get('ultima_respuesta') or 'Sin respuesta registrada.'}")


@_dialog("Responder reclamo", width="large")
def modal_responder(reclamo: dict):
    st.write(f"**Reclamo:** {reclamo['descripcion']}")
    st.write(f"**Ultima respuesta:** {reclamo.get('ultima_respuesta') or '(ninguna)'}")
    nueva = st.text_area("Nueva respuesta al cliente", height=120)
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Enviar respuesta", type="primary", disabled=not nueva.strip()):
            resp = _post(f"/reclamos/{reclamo['id']}/responder", json={"texto": nueva.strip()})
            if resp.status_code == 200:
                st.success("Respuesta registrada.")
                st.rerun()
            else:
                st.error(f"Error: {resp.text}")
    with col_b:
        resolucion = st.text_input("Resolucion (para cerrar)")
        if st.button("Cerrar reclamo", disabled=not resolucion.strip()):
            resp = _post(f"/reclamos/{reclamo['id']}/cerrar", json={"texto": resolucion.strip()})
            if resp.status_code == 200:
                st.success("Reclamo cerrado.")
                st.rerun()
            else:
                st.error(f"Error: {resp.text}")


@_dialog("Analisis IA — Plan de seguimiento y mail sugerido", width="large")
def modal_ia(reclamo: dict):
    st.write(f"**Cliente:** {reclamo['cliente_id']}  |  CUIT: {reclamo.get('cuit', '')}")
    with st.spinner("Analizando historial con IA..."):
        resp = _post(f"/reclamos/{reclamo['id']}/analizar")
    if resp.status_code != 200:
        st.error(f"Error al analizar: {resp.text}")
        return
    data = resp.json()
    st.caption(f"Reclamos del cliente analizados: {data['total_reclamos_cliente']}")
    tab_analisis, tab_mail = st.tabs(["Analisis y plan de accion", "Borrador de mail"])
    with tab_analisis:
        st.markdown(data["analisis"])
    with tab_mail:
        email = data.get("email_sugerido", "")
        if email:
            st.write(f"**Para:** {data.get('mail_destino', '')}")
            st.text_area("Borrador listo para copiar", value=email, height=400, key="ia_mail_body")
        else:
            st.info("No se genero borrador de mail.")


# ------------------------------------------------------------------
# Tabla de reclamos
# ------------------------------------------------------------------
COLS = [2, 4, 1.2, 1.2, 1.2, 0.9, 1.2, 0.9]
LABELS = ["Cliente", "Descripcion", "Inicio", "Cierre", "Estado", "Ver", "Resp", "IA"]

headers = st.columns(COLS)
for col, label in zip(headers, LABELS):
    col.markdown(f"**{label}**")

st.divider()

for r in reclamos:
    cols = st.columns(COLS)
    cols[0].write(f"{r['cliente_id']}  \n`{r.get('cuit','')}`")
    desc = (r.get("descripcion") or "")
    cols[1].write(desc[:80] + ("..." if len(desc) > 80 else ""))
    cols[2].write(r.get("fecha_inicio") or "-")
    cols[3].write(r.get("fecha_cierre") or "-")
    cols[4].write("Abierto" if r["activo"] else "Cerrado")

    if cols[5].button("Ver", key=f"hist_{r['id']}"):
        modal_historial(r)
    if r["activo"] and cols[6].button("Resp", key=f"resp_{r['id']}"):
        modal_responder(r)
    if cols[7].button("IA", key=f"ia_{r['id']}"):
        modal_ia(r)

    st.divider()
