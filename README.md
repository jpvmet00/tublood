# Sistema de Conciliacion de Cobros — TUBLOOD SA

Automatizacion de conciliacion de facturas con extractos bancarios (Banco Macro y Banco Galicia).
Backend **FastAPI + SQLAlchemy**, frontend **Streamlit**, base de datos **SQLite**.

---

## Estructura del proyecto

```
TUBLOOD/
├── app/
│   ├── main.py                  # FastAPI app
│   ├── config.py                # Settings via .env
│   ├── db/
│   │   ├── models.py            # Tablas: facturas, movimientos_banco, conciliaciones, padron, reclamos
│   │   └── session.py           # Engine + SessionLocal
│   ├── adapters/
│   │   ├── base.py              # BankAdapter ABC
│   │   ├── macro.py             # Banco Macro (.xls/.xlsx)
│   │   ├── galicia.py           # Banco Galicia (.xlsx)
│   │   └── factory.py           # Auto-deteccion de banco
│   ├── services/
│   │   ├── ingestion.py         # Carga Libro3.xlsx -> DB
│   │   └── conciliation.py      # Cruza movimientos con facturas (FIFO, tolerancia 10%)
│   ├── routers/
│   │   ├── upload.py            # POST /upload/facturas, /upload/banco, /upload/banco/detect
│   │   └── conciliation.py      # GET /conciliacion/vencidas, /historial, /resumen
│   └── schemas/
│       ├── bank_movement.py     # MovimientoCanonical (Pydantic)
│       └── factura.py           # FacturaOut, ConciliacionOut
├── frontend/
│   ├── app.py                   # Entry point Streamlit
│   └── pages/
│       ├── 01_upload.py         # Subir Libro3 + extracto banco (con deteccion)
│       └── 02_dashboard.py      # KPIs + facturas vencidas + historial
├── tests/                       # 90 tests, 96% coverage
├── data/                        # Archivos Excel fuente
├── notebooks/                   # Notebook exploratorio original
├── requirements.txt
├── pytest.ini
└── .env.example
```

---

## Requisitos

Python 3.9+. Sin dependencias externas fuera de Python (no necesita Telegram, n8n ni nada adicional).

```bash
pip install -r requirements.txt
```

---

## Levantar el sistema

Desde la carpeta `TUBLOOD/`:

### 1. Copiar y editar el archivo de configuracion

```bash
cp .env.example .env
```

El unico campo obligatorio para correr localmente es `DATABASE_URL` (ya tiene valor por defecto).
El resto (Telegram, SMTP) es opcional y corresponde a fases futuras.

### 2. Levantar la API

```bash
python -m uvicorn app.main:app --port 8000 --reload
```

La DB SQLite se crea automaticamente al iniciar. La API queda en `http://localhost:8000`.

### 3. Levantar el frontend

En otra terminal:

```bash
python3 -m streamlit run frontend/app.py
```

El frontend queda en `http://localhost:8501`.

---

## Flujo de uso

### Paso 1 — Cargar facturas

En el frontend, pagina "Subir archivos", seccion 1:

- Seleccionar `Libro3.xlsx` (sheet `pendientes` con columnas NRO, CLIENTE, CUIT, IMPORTE, SALDO, FECHA, VENCIMIENTO, CONDICION, VENDEDOR, EMAIL)
- Clic en "Subir facturas"
- El sistema hace upsert: actualiza las existentes, agrega las nuevas
- El padron CUIT <-> cliente se arma automaticamente a partir de los CUITs en las facturas

### Paso 2 — Cargar extracto del banco y conciliar

En la seccion 2 del mismo panel:

1. Seleccionar el archivo exportado del banco (Macro `.xls`/`.xlsx` o Galicia `.xlsx`)
2. El sistema detecta automaticamente el banco y muestra la informacion de la cuenta:
   - Ejemplo: "Banco Galicia — Caja Ahorro Pesos N° ...8190105"
   - Ejemplo: "Banco Macro — Caja de Ahorro PESOS N° 451806976969666"
3. Confirmar para procesar
4. El sistema:
   - Parsea solo los creditos (ingresos) del extracto
   - Extrae el CUIT de cada movimiento
   - Cruza CUIT -> cliente -> facturas pendientes
   - Aplica FIFO: paga primero las facturas de vencimiento mas antiguo
   - Tolerancia del 10%: un cobro de $9.500 cierra una factura de $10.000
   - Clasifica cada factura: `cobrado_total` o `cobrado_parcial`
   - Marca el saldo restante

### Paso 3 — Ver vencidas y gestionar reclamos

En el frontend, pagina "Dashboard":

- KPIs: total facturas, con saldo pendiente, cobradas, vencidas, saldo total
- Tabla de facturas vencidas con saldo, ordenadas por vencimiento
- Historial de conciliaciones ejecutadas

---

## Bancos soportados

| Banco | Extension | Como detecta el CUIT | Creditos |
|---|---|---|---|
| Banco Macro | `.xls` / `.xlsx` | Campo `CONCEPTO`: `TRANSF:XXXX-27218826488` | `IMPORTE > 0` |
| Banco Galicia | `.xlsx` | Campo `Movimiento` multilinea, linea que contiene solo 10-11 digitos | Columna `Credito > 0` |

Para agregar otro banco: crear `app/adapters/nuevo_banco.py` heredando de `BankAdapter` e incluirlo en `factory.py`.

---

## API endpoints

| Metodo | Endpoint | Descripcion |
|---|---|---|
| `GET` | `/health` | Estado de la API |
| `POST` | `/upload/facturas` | Sube Libro3.xlsx y hace upsert de facturas |
| `POST` | `/upload/banco/detect` | Detecta el banco sin persistir nada |
| `POST` | `/upload/banco` | Ingesta movimientos y ejecuta conciliacion |
| `GET` | `/conciliacion/vencidas` | Facturas vencidas con saldo > 0 |
| `GET` | `/conciliacion/historial` | Ultimas conciliaciones ejecutadas |
| `GET` | `/conciliacion/resumen` | KPIs generales |

Documentacion interactiva: `http://localhost:8000/docs`

---

## Correr los tests

```bash
cd TUBLOOD/
pytest
```

Los tests usan una base SQLite en archivo temporal, no tocan la DB de desarrollo.
Fixtures sinteticos en `tests/fixtures/` (generados por `tests/fixtures/make_fixtures.py`).

---

## Reglas de negocio configurables

En `.env` o directamente en `app/config.py`:

| Variable | Default | Descripcion |
|---|---|---|
| `COOLDOWN_DIAS` | 7 | Dias minimos entre reclamos al mismo cliente |
| `MORA_MINIMA` | 1 | Dias de mora minimos para aparecer en vencidas |
| `TOLERANCE_PCT` | 0.10 | Tolerancia de monto para match (10%) |
| `DATABASE_URL` | `sqlite:///./tublood.db` | URL de base de datos |

---

## Troubleshooting

**Puerto 8000 ocupado**
```bash
lsof -ti:8000 | xargs kill
```

**ModuleNotFoundError al iniciar**
```bash
pip install -r requirements.txt
```

**El archivo del banco no se reconoce**
- Macro: verificar que la primera celda del archivo diga "Ultimos Movimientos"
- Galicia: verificar que la primera celda diga "Banco Galicia"
- Si el formato cambio, revisar `app/adapters/macro.py` o `app/adapters/galicia.py`

**Conciliacion no matchea movimientos**
- Verificar que los CUITs de las facturas coincidan con los del extracto
- La tolerancia por defecto es 10%; se puede ajustar con `TOLERANCE_PCT` en `.env`
- Los movimientos con fecha de hoy se ignoran (se procesa solo hasta ayer)
