import streamlit as st
import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.dirname(__file__)))
from style import inject_css
import httpx
import pandas as pd
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")

inject_css()

# Compatibilidad st.dialog: disponible como st.dialog (1.36+) o st.experimental_dialog (1.33-1.35)
_dialog = getattr(st, "dialog", getattr(st, "experimental_dialog", None))


def _get(path: str):
    try:
        resp = httpx.get(f"{API_URL}{path}", timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        st.error(f"No se pudo conectar con la API: {exc}")
        return None


def _get_raw(path: str):
    return httpx.get(f"{API_URL}{path}", timeout=15)


def _post(path: str, **kw):
    return httpx.post(f"{API_URL}{path}", timeout=60, **kw)


st.title("Conciliacion")

col_nav, _ = st.columns([1, 3])
with col_nav:
    st.markdown(
        """<a href="/movimientos_bancarios" target="_self"
           style="display:inline-block;background:linear-gradient(135deg,#1565C0,#0288D1);
                  color:white;font-weight:600;padding:8px 18px;border-radius:6px;
                  text-decoration:none;font-size:0.88rem;">
            Cargar movimientos bancarios
        </a>""",
        unsafe_allow_html=True,
    )

st.divider()

# --- Reset DB ---
with st.expander("Administracion", expanded=False):
    st.warning("Esta accion elimina TODOS los datos de la base de datos y no se puede deshacer.")
    confirmar = st.text_input("Escribi CONFIRMAR para habilitar el boton")
    if st.button("Resetear base de datos", disabled=(confirmar != "CONFIRMAR"), type="primary"):
        resp = _post("/admin/reset-db")
        if resp.status_code == 200:
            st.success("Base de datos reiniciada. Recarga la pagina.")
            st.rerun()
        else:
            st.error(f"Error: {resp.text}")

st.divider()

# --- KPIs ---
resumen = _get("/conciliacion/resumen")
if resumen:
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total facturas", resumen["total_facturas"])
    c2.metric("Con saldo pendiente", resumen["con_saldo_pendiente"])
    c3.metric("Cobradas", resumen["cobradas"])
    c4.metric("Vencidas", resumen["vencidas"])
    c5.metric("Reclamos abiertos", resumen.get("reclamos_abiertos", 0))
    c6.metric("Saldo total ($)", f"{resumen['saldo_total']:,.0f}")

st.divider()

# --- Facturas vencidas ---
st.header("Facturas vencidas con saldo")

mora = st.number_input("Mora minima (dias)", min_value=0, value=1, step=1)
vencidas = _get(f"/conciliacion/vencidas?mora_minima={mora}&limit=200")


@_dialog("Mail de solicitud de pago", width="large")
def modal_mail_cobro(cliente_id: str):
    resp = _post("/conciliacion/mail-cobro", json={"cliente_id": cliente_id})
    if resp.status_code != 200:
        st.error(f"Error: {resp.text}")
        return
    data = resp.json()
    if "error" in data:
        st.warning(data["error"])
        return
    st.write(f"**Para:** {data['mail_to'] or '(sin mail configurado)'}")
    st.write(f"**Asunto:** {data['asunto']}")
    st.divider()
    st.text_area("Cuerpo del mail", value=data["cuerpo"], height=400, key="mail_body")
    st.caption(
        f"Facturas incluidas: {data['total_facturas']} | "
        f"Vencidas: {data['facturas_vencidas']} | "
        f"Saldo total: ${data['saldo_total']:,.0f}"
    )


if vencidas:
    df = pd.DataFrame(vencidas)
    if df.empty:
        st.info("No hay facturas vencidas con los filtros actuales.")
    else:
        # Consultar riesgo crediticio (solo cache, sin llamadas externas en cada render)
        cuits_unicos = [c for c in df["cuit"].dropna().unique().tolist() if c]
        riesgo_map = {}
        if cuits_unicos:
            try:
                resp_r = _post("/riesgo/bulk", json=cuits_unicos)
                if resp_r.status_code == 200:
                    riesgo_map = resp_r.json()
            except Exception:
                pass

        def _label_riesgo(cuit):
            if not cuit or cuit not in riesgo_map:
                return "Sin consultar"
            r = riesgo_map[cuit]
            return f"[{r['situacion']}] {r['label']}"

        df["riesgo_bcra"] = df["cuit"].apply(_label_riesgo)
        df["solicitar_pago"] = False

        # Alerta de CUITs con situacion >= 3
        cuits_alerta = [c for c, r in riesgo_map.items() if r.get("alerta")]
        if cuits_alerta:
            clientes_alerta = df[df["cuit"].isin(cuits_alerta)]["razon_social"].dropna().unique()
            st.warning(
                f"Riesgo crediticio BCRA: {len(cuits_alerta)} cliente(s) con situacion 3 o superior — "
                + ", ".join(clientes_alerta[:5])
            )

        col_act, _ = st.columns([1, 4])
        with col_act:
            if st.button("Actualizar riesgo BCRA", help="Consulta el BCRA para todos los CUITs de la lista"):
                with st.spinner("Consultando BCRA..."):
                    for cuit in cuits_unicos:
                        try:
                            _get_raw(f"/riesgo/{cuit}?forzar=true")
                        except Exception:
                            pass
                st.rerun()

        cols_order = [c for c in [
            "solicitar_pago", "nro_factura", "razon_social", "cliente_id",
            "cuit", "saldo", "fecha_vencimiento", "dias_vencida",
            "condicion_venta", "reclamo_activo", "riesgo_bcra"
        ] if c in df.columns]

        edited = st.data_editor(
            df[cols_order],
            column_config={
                "solicitar_pago": st.column_config.CheckboxColumn("Solicitar pago", default=False),
                "reclamo_activo": st.column_config.CheckboxColumn("Reclamo activo", disabled=True),
                "saldo": st.column_config.NumberColumn("Saldo $", format="$ %.0f"),
                "dias_vencida": st.column_config.NumberColumn("Dias vencida"),
                "riesgo_bcra": st.column_config.TextColumn("Riesgo BCRA", disabled=True),
            },
            disabled=[c for c in cols_order if c != "solicitar_pago"],
            use_container_width=True,
            hide_index=True,
            key="tabla_vencidas",
        )

        seleccionadas = edited[edited["solicitar_pago"] == True]

        if not seleccionadas.empty:
            reclamo_col = "reclamo_activo" if "reclamo_activo" in seleccionadas.columns else None
            con_reclamo = seleccionadas[seleccionadas[reclamo_col] == True] if reclamo_col else pd.DataFrame()

            if not con_reclamo.empty:
                st.warning(
                    f"Atencion: {len(con_reclamo)} factura(s) seleccionada(s) tienen reclamos activos. "
                    "Revisa la pagina de Reclamos antes de solicitar el pago."
                )
                st.dataframe(
                    con_reclamo[["nro_factura", "razon_social", "saldo"]],
                    use_container_width=True, hide_index=True,
                )

            clientes_sel = seleccionadas["cliente_id"].unique()
            st.write(f"**{len(seleccionadas)} factura(s) en {len(clientes_sel)} cliente(s):**")
            for cid in clientes_sel:
                sub = seleccionadas[seleccionadas["cliente_id"] == cid]
                razon = sub["razon_social"].iloc[0] or cid
                saldo_sub = sub["saldo"].sum()
                col_a, col_b = st.columns([3, 1])
                col_a.write(f"{razon} — {len(sub)} factura(s) — ${saldo_sub:,.0f}")
                if col_b.button("Ver mail", key=f"mail_{cid}"):
                    modal_mail_cobro(cid)

        total_saldo = df["saldo"].sum()
        st.caption(f"Total saldo vencido: ${total_saldo:,.0f}")

st.divider()

# --- Historial conciliaciones ---
st.header("Ultimas conciliaciones")

historial = _get("/conciliacion/historial?limit=100")
if historial:
    df_h = pd.DataFrame(historial)
    if df_h.empty:
        st.info("Sin conciliaciones registradas.")
    else:
        st.dataframe(df_h, use_container_width=True, hide_index=True)
