import streamlit as st
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from style import inject_css
import httpx

st.set_page_config(
    page_title="TUBLOOD - Conciliacion",
    page_icon="T",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

API_URL = os.getenv("API_URL", "http://localhost:8000")

# ── Hero ───────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="
        background: linear-gradient(135deg, #1565C0 0%, #0288D1 100%);
        border-radius: 16px;
        padding: 52px 44px;
        margin-bottom: 36px;
    ">
        <div style="font-size:0.78rem;text-transform:uppercase;letter-spacing:0.12em;
                    color:rgba(255,255,255,0.72);margin-bottom:10px;">
            Plataforma de gestion financiera
        </div>
        <div style="font-size:2.6rem;font-weight:800;color:white;
                    margin:0 0 14px 0;line-height:1.15;font-family:inherit;">
            TUBLOOD &mdash; Conciliacion de Cobros
        </div>
        <p style="font-size:1.1rem;color:rgba(255,255,255,0.88);max-width:680px;
                  margin:0 0 28px 0;line-height:1.65;">
            Automatiza la conciliacion bancaria contra tus facturas pendientes.
            Detecta pagos, gestiona reclamos y genera mails de cobranza con IA
            &mdash; todo desde una interfaz web, sin codigo.
        </p>
        <div style="display:flex;gap:12px;flex-wrap:wrap;">
            <span style="background:rgba(255,255,255,0.18);border-radius:20px;
                         padding:6px 16px;font-size:0.82rem;color:white;">
                Banco Macro
            </span>
            <span style="background:rgba(255,255,255,0.18);border-radius:20px;
                         padding:6px 16px;font-size:0.82rem;color:white;">
                Banco Galicia
            </span>
            <span style="background:rgba(255,255,255,0.18);border-radius:20px;
                         padding:6px 16px;font-size:0.82rem;color:white;">
                IA con GPT-4o
            </span>
            <span style="background:rgba(255,255,255,0.18);border-radius:20px;
                         padding:6px 16px;font-size:0.82rem;color:white;">
                Docker listo
            </span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Estado actual ──────────────────────────────────────────────────────────────
try:
    resp = httpx.get(f"{API_URL}/conciliacion/resumen", timeout=5)
    if resp.status_code == 200:
        r = resp.json()
        st.markdown("### Estado del sistema")
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Facturas cargadas", r["total_facturas"])
        col2.metric("Con saldo pendiente", r["con_saldo_pendiente"])
        col3.metric("Cobradas", r["cobradas"])
        col4.metric("Vencidas", r["vencidas"])
        col5.metric("Reclamos abiertos", r.get("reclamos_abiertos", 0))

        if r["total_facturas"] == 0:
            st.info("Para empezar: carga el padron de clientes y las facturas desde Datos Maestros.")
        elif r["vencidas"] > 0:
            st.warning(f"Hay {r['vencidas']} factura(s) vencida(s) con saldo pendiente. Revisa Conciliacion.")
        else:
            st.success("Sistema al dia. Sin facturas vencidas pendientes.")
    else:
        st.error("API no disponible. Asegurate de que el backend este corriendo.")
except Exception:
    st.warning("No se puede conectar con la API. Seguir las instrucciones de instalacion para iniciar el sistema.")

st.divider()

# ── Como funciona ──────────────────────────────────────────────────────────────
st.markdown("## Como funciona")

_card = """
<div style="background:{bg};border-radius:12px;padding:24px 20px;
            border-left:4px solid {border};height:100%;">
    <div style="font-size:1.6rem;font-weight:900;color:{border};margin-bottom:6px;">{num}</div>
    <div style="font-weight:700;font-size:1rem;margin-bottom:8px;color:#222;">{title}</div>
    <div style="font-size:0.87rem;color:#666;line-height:1.55;">{body}</div>
</div>"""

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(_card.format(
        bg="rgba(21,101,192,0.08)", border="#1565C0", num="01",
        title="Cargas las Facturas",
        body="Exporta las facturas pendientes desde tu ERP y subelas en Datos Maestros. "
             "El sistema detecta saldos, vencimientos y condiciones de pago.",
    ), unsafe_allow_html=True)

with c2:
    st.markdown(_card.format(
        bg="rgba(2,136,209,0.08)", border="#0288D1", num="02",
        title="Cargas el Padron",
        body="Vincula cada CUIT con su cliente interno. "
             "Soporta mails de reclamo y atencion al cliente. "
             "Se actualiza de forma incremental.",
    ), unsafe_allow_html=True)

with c3:
    st.markdown(_card.format(
        bg="rgba(1,87,155,0.08)", border="#01579B", num="03",
        title="Subes los Extractos",
        body="Arrastra los archivos del home banking de Macro y/o Galicia. "
             "El sistema detecta el banco y concilia creditos contra facturas por CUIT (FIFO, tolerancia 10%).",
    ), unsafe_allow_html=True)

with c4:
    st.markdown(_card.format(
        bg="rgba(230,74,25,0.06)", border="#E64A19", num="04",
        title="Gestionas Reclamos",
        body="Facturas vencidas generan reclamos con historial completo. "
             "Un agente GPT-4o analiza el contexto y genera un borrador de mail o plan de accion.",
    ), unsafe_allow_html=True)

st.divider()

# ── Instalacion con Docker ─────────────────────────────────────────────────────
st.markdown("## Instalacion con Docker")
st.markdown(
    "La forma mas rapida de correr TUBLOOD en cualquier maquina es con Docker. "
    "No necesitas instalar Python ni configurar dependencias."
)

col_steps, col_cmd = st.columns([1, 1])

with col_steps:
    st.markdown(
        """
        <div style="background:rgba(21,101,192,0.07);border-radius:12px;padding:24px;height:100%;">
        <div style="font-weight:700;font-size:1rem;margin-bottom:16px;color:#1565C0;">
            Pasos
        </div>
        <ol style="margin:0;padding-left:20px;line-height:2.2;font-size:0.9rem;color:#444;">
            <li>Instala <strong>Docker Desktop</strong><br>
                <code style="font-size:0.8rem;">docker.com/get-started</code>
            </li>
            <li>Abri Docker Desktop y espera a que este corriendo</li>
            <li>Clona el repositorio o descarga el ZIP</li>
            <li>Crea el archivo <code>.env</code> con tu clave de OpenAI<br>
                <code style="font-size:0.8rem;">OPENAI_API_KEY=sk-proj-...</code>
            </li>
            <li>Ejecuta el comando en la terminal</li>
            <li>Abri el navegador en <code>localhost:8501</code></li>
        </ol>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_cmd:
    st.markdown(
        """
        <div style="background:#0d1117;border-radius:12px;padding:28px;font-family:monospace;height:100%;box-sizing:border-box;">
        <div style="color:#58a6ff;font-size:0.75rem;margin-bottom:14px;
                    text-transform:uppercase;letter-spacing:0.1em;font-family:monospace;">
            Terminal
        </div>
        <div style="color:#8b949e;font-size:0.8rem;margin-bottom:3px;">
            # Crear configuracion
        </div>
        <div style="color:#e6edf3;font-size:0.87rem;margin-bottom:18px;
                    background:rgba(255,255,255,0.05);padding:8px 10px;border-radius:4px;">
            echo "OPENAI_API_KEY=sk-proj-..." &gt; .env
        </div>
        <div style="color:#8b949e;font-size:0.8rem;margin-bottom:3px;">
            # Construir y levantar
        </div>
        <div style="color:#e6edf3;font-size:0.87rem;margin-bottom:22px;
                    background:rgba(255,255,255,0.05);padding:8px 10px;border-radius:4px;">
            docker-compose up --build
        </div>
        <div style="color:#8b949e;font-size:0.8rem;margin-bottom:8px;">
            # Accesos:
        </div>
        <div style="color:#3fb950;font-size:0.87rem;margin-bottom:4px;">
            Frontend &nbsp; http://localhost:8501
        </div>
        <div style="color:#3fb950;font-size:0.87rem;">
            API &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; http://localhost:8000
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <div style="background:rgba(21,101,192,0.06);border:1px solid rgba(21,101,192,0.2);
                border-radius:8px;padding:14px 20px;margin-top:14px;font-size:0.87rem;color:#444;">
        <strong>Sin Docker</strong> &mdash; requiere Python 3.11+.<br>
        Backend: <code>uvicorn app.main:app --port 8000 --reload</code><br>
        Frontend: <code>streamlit run frontend/app.py</code> (en otra terminal)
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# ── Imagenes de producto ───────────────────────────────────────────────────────
st.markdown("## Lineas de producto")
st.caption(
    "Para agregar imagenes: copia los archivos .jpg/.png a frontend/static/ "
    "y reemplaza los bloques de placeholder con st.image('frontend/static/imagen.jpg')."
)

_img_card = """
<div style="border:1px solid #e0e0e0;border-radius:12px;overflow:hidden;
            background:#f8f9fa;text-align:center;">
    <div style="
        background: linear-gradient(135deg, {grad_a} 0%, {grad_b} 100%);
        height: 200px;
        display: flex;
        align-items: center;
        justify-content: center;
    ">
        <div style="color:white;font-size:0.85rem;opacity:0.8;letter-spacing:0.05em;">
            {placeholder}
        </div>
    </div>
    <div style="padding:18px;">
        <div style="font-weight:700;font-size:1rem;color:#222;margin-bottom:6px;">{title}</div>
        <div style="font-size:0.85rem;color:#666;line-height:1.55;">{desc}</div>
    </div>
</div>"""

img_col1, img_col2 = st.columns(2)

with img_col1:
    st.markdown(
        _img_card.format(
            grad_a="#1565C0", grad_b="#0288D1",
            placeholder="Insertar imagen de producto",
            title="Linea Venopuncion",
            desc="Agujas de toma multiple, mariposas y accesorios para extraccion de sangre venosa.",
        ),
        unsafe_allow_html=True,
    )
    if os.path.exists(os.path.join(os.path.dirname(__file__), "static", "venopuncion.jpg")):
        st.image("frontend/static/venopuncion.jpg", use_container_width=True)

with img_col2:
    st.markdown(
        _img_card.format(
            grad_a="#0288D1", grad_b="#26C6DA",
            placeholder="Insertar imagen de producto",
            title="Linea Plasma Rico en Plaquetas",
            desc="Tubos y kits de centrifugacion para la obtencion y procesamiento de PRP.",
        ),
        unsafe_allow_html=True,
    )
    if os.path.exists(os.path.join(os.path.dirname(__file__), "static", "prp.jpg")):
        st.image("frontend/static/prp.jpg", use_container_width=True)

st.divider()

# ── Orden de carga ─────────────────────────────────────────────────────────────
st.markdown("## Orden de carga recomendado")

st.markdown("""
| Paso | Archivo | Seccion | Por que primero |
|------|---------|---------|-----------------|
| 1 | `padron_clientes.xlsx` | Datos Maestros > Padron de Clientes | Vincula CUIT con cliente ID antes de procesar facturas y movimientos |
| 2 | `Facturas_ERP.xlsx` | Datos Maestros > Carga de Facturas | Carga las facturas pendientes con sus saldos |
| 3 | Extractos del banco | Cargar Movimientos Bancarios | Concilia los creditos bancarios contra las facturas ya cargadas |
| 4 | `reclamos_demo.xlsx` | Reclamos | Opcional — carga historial de reclamos existentes |
""")

st.divider()

# ── Bancos soportados ──────────────────────────────────────────────────────────
st.markdown("## Bancos soportados")

col_a, col_b, col_c = st.columns([1, 1, 2])

with col_a:
    st.markdown(
        """
        <div style="border:2px solid #1565C0;border-radius:12px;padding:24px;text-align:center;height:100%;">
            <div style="font-size:1.4rem;font-weight:800;color:#1565C0;margin-bottom:10px;">
                Banco Macro
            </div>
            <div style="color:#666;font-size:0.85rem;line-height:1.7;">
                Formato .xls / .xlsx<br>
                Deteccion automatica<br>
                Extrae CUIT del concepto
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_b:
    st.markdown(
        """
        <div style="border:2px solid #0288D1;border-radius:12px;padding:24px;text-align:center;height:100%;">
            <div style="font-size:1.4rem;font-weight:800;color:#0288D1;margin-bottom:10px;">
                Banco Galicia
            </div>
            <div style="color:#666;font-size:0.85rem;line-height:1.7;">
                Formato .xlsx<br>
                Deteccion automatica<br>
                Extrae CUIT y razon social
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_c:
    st.markdown(
        """
        <div style="border:1px solid #ccc;border-radius:12px;padding:24px;height:100%;">
            <div style="font-weight:700;color:#333;margin-bottom:10px;font-size:1rem;">
                Logica de conciliacion
            </div>
            <div style="color:#666;font-size:0.87rem;line-height:1.65;">
                Cada credito bancario se matchea contra facturas pendientes del mismo CUIT
                ordenadas por vencimiento (FIFO).<br><br>
                Tolerancia configurable (default 10%).
                Un credito puede cubrir multiples facturas.
                El saldo se actualiza en tiempo real.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
