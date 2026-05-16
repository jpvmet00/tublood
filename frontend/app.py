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
        <h1 style="color:white !important;border:none !important;font-size:2.6rem;
                   margin:0 0 14px 0;padding:0;line-height:1.15;">
            TUBLOOD &mdash; Conciliacion de Cobros
        </h1>
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
            st.info("Para empezar: ve a Datos Maestros y carga el padron de clientes y el Libro3.")
        elif r["vencidas"] > 0:
            st.warning(f"Hay {r['vencidas']} factura(s) vencida(s) con saldo pendiente. Revisa el Dashboard.")
        else:
            st.success("Sistema al dia. Sin facturas vencidas pendientes.")
    else:
        st.error("API no disponible. Asegurate de que el backend este corriendo.")
except Exception:
    st.warning("No se puede conectar con la API. Sigue las instrucciones de instalacion para iniciar el sistema.")

st.divider()

# ── Como funciona ──────────────────────────────────────────────────────────────
st.markdown("## Como funciona")

CARD_STYLE = """
    background: {bg};
    border-radius: 12px;
    padding: 24px 20px;
    height: 100%;
    border-left: 4px solid {border};
"""

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(
        f"""<div style="{CARD_STYLE.format(bg='rgba(21,101,192,0.08)', border='#1565C0')}">
        <div style="font-size:1.6rem;font-weight:900;color:#1565C0;margin-bottom:6px;">01</div>
        <div style="font-weight:700;font-size:1rem;margin-bottom:8px;">Cargas el Libro3</div>
        <div style="font-size:0.87rem;color:#666;line-height:1.55;">
        Subi el archivo de facturas pendientes. El sistema detecta saldos,
        fechas de vencimiento y condiciones de pago de cada cliente.
        </div></div>""",
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        f"""<div style="{CARD_STYLE.format(bg='rgba(2,136,209,0.08)', border='#0288D1')}">
        <div style="font-size:1.6rem;font-weight:900;color:#0288D1;margin-bottom:6px;">02</div>
        <div style="font-weight:700;font-size:1rem;margin-bottom:8px;">Cargas el padron</div>
        <div style="font-size:0.87rem;color:#666;line-height:1.55;">
        Vincula cada CUIT con su cliente interno.
        Soporta mails de reclamo y atencion al cliente.
        Se actualiza de forma incremental.
        </div></div>""",
        unsafe_allow_html=True,
    )

with c3:
    st.markdown(
        f"""<div style="{CARD_STYLE.format(bg='rgba(1,87,155,0.08)', border='#01579B')}">
        <div style="font-size:1.6rem;font-weight:900;color:#01579B;margin-bottom:6px;">03</div>
        <div style="font-weight:700;font-size:1rem;margin-bottom:8px;">Subes los extractos</div>
        <div style="font-size:0.87rem;color:#666;line-height:1.55;">
        Arrastra los archivos del home banking de Macro y/o Galicia.
        El sistema detecta el banco y concilia creditos contra facturas por CUIT (FIFO, tolerancia 10%).
        </div></div>""",
        unsafe_allow_html=True,
    )

with c4:
    st.markdown(
        f"""<div style="{CARD_STYLE.format(bg='rgba(230,74,25,0.06)', border='#E64A19')}">
        <div style="font-size:1.6rem;font-weight:900;color:#E64A19;margin-bottom:6px;">04</div>
        <div style="font-weight:700;font-size:1rem;margin-bottom:8px;">Gestionas reclamos</div>
        <div style="font-size:0.87rem;color:#666;line-height:1.55;">
        Facturas vencidas generan reclamos con historial. Un agente GPT-4o analiza
        el contexto y genera un borrador de mail o plan de accion.
        </div></div>""",
        unsafe_allow_html=True,
    )

st.divider()

# ── Instalacion con Docker ─────────────────────────────────────────────────────
st.markdown("## Instalacion con Docker")
st.markdown(
    "La forma mas rapida de correr TUBLOOD en cualquier maquina es con Docker. "
    "No necesitas instalar Python ni dependencias."
)

col_steps, col_cmd = st.columns([1, 1])

with col_steps:
    st.markdown(
        """
        <div style="background:rgba(21,101,192,0.07);border-radius:12px;padding:24px;">
        <div style="font-weight:700;font-size:1rem;margin-bottom:16px;color:#1565C0;">
            Pasos
        </div>
        <ol style="margin:0;padding-left:20px;line-height:2;font-size:0.9rem;color:#444;">
            <li>Instala <strong>Docker Desktop</strong> desde
                <code>docker.com/get-started</code>
            </li>
            <li>Abri Docker Desktop y espera a que este corriendo</li>
            <li>Clona el repositorio o descarga el ZIP</li>
            <li>Crea un archivo <code>.env</code> con tu clave de OpenAI</li>
            <li>Ejecuta el comando de la derecha en la terminal</li>
            <li>Abri el navegador en <code>localhost:8501</code></li>
        </ol>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_cmd:
    st.markdown(
        """
        <div style="background:#0d1117;border-radius:12px;padding:24px;font-family:monospace;">
        <div style="color:#58a6ff;font-size:0.78rem;margin-bottom:12px;
                    text-transform:uppercase;letter-spacing:0.08em;">
            Terminal
        </div>
        <div style="color:#8b949e;font-size:0.82rem;margin-bottom:4px;">
            # 1. Crear el archivo de configuracion
        </div>
        <div style="color:#e6edf3;font-size:0.88rem;margin-bottom:16px;">
            echo "OPENAI_API_KEY=sk-proj-..." &gt; .env
        </div>
        <div style="color:#8b949e;font-size:0.82rem;margin-bottom:4px;">
            # 2. Construir y levantar los servicios
        </div>
        <div style="color:#e6edf3;font-size:0.88rem;margin-bottom:16px;">
            docker-compose up --build
        </div>
        <div style="color:#8b949e;font-size:0.82rem;margin-bottom:4px;">
            # Accesos una vez levantado:
        </div>
        <div style="color:#3fb950;font-size:0.88rem;margin-bottom:4px;">
            Frontend  -&gt;  http://localhost:8501
        </div>
        <div style="color:#3fb950;font-size:0.88rem;">
            API       -&gt;  http://localhost:8000
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <div style="background:rgba(21,101,192,0.06);border:1px solid rgba(21,101,192,0.2);
                border-radius:8px;padding:14px 20px;margin-top:12px;font-size:0.87rem;color:#444;">
        <strong>Sin Docker:</strong> necesitas Python 3.11+.
        Instala dependencias con <code>pip install -r requirements.txt</code>,
        luego corre el backend con
        <code>uvicorn app.main:app --port 8000 --reload</code>
        y el frontend con <code>streamlit run frontend/app.py</code> en otra terminal.
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# ── Orden de carga ─────────────────────────────────────────────────────────────
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
