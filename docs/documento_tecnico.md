# Documento Tecnico — TUBLOOD Sistema de Conciliacion

## 1. Que resuelve este sistema

TUBLOOD SA gestiona cobranzas de productos medicos (tubos, agujas, kits diagnostico) a hospitales, clinicas y distribuidores. El ciclo de cobranza tiene tres fricciones principales que este sistema resuelve:

**Friccion 1 — Identificacion manual de pagos**
Los creditos bancarios llegan sin referencia de factura. El area de administracion cruzaba manualmente cada deposito contra el listado de facturas pendientes exportado del ERP. Con volumenes altos de clientes, este proceso toma horas por semana y tiene errores de asignacion.

**Friccion 2 — Seguimiento disperso de deuda vencida**
Las facturas vencidas vivian en planillas Excel separadas del historial de reclamos. No habia trazabilidad de cuantas veces se contacto al cliente ni que se le dijo, lo que generaba contactos duplicados o clientes sin seguimiento.

**Friccion 3 — Falta de visibilidad financiera ejecutiva**
No existia un dashboard centralizado que mostrara en tiempo real el saldo vencido total, la distribucion por cliente y el comportamiento historico de pagos.

---

## 2. Stack actual implementado

| Capa | Tecnologia | Version |
|------|-----------|---------|
| API backend | FastAPI | 0.111 |
| ORM / DB | SQLAlchemy + SQLite | 2.0 / — |
| Procesamiento datos | Pandas, openpyxl, xlrd | 2.2 / 3.1 / 2.0 |
| Frontend | Streamlit | 1.35 |
| IA (reclamos) | OpenAI gpt-4o-mini | API |
| Containerizacion | Docker + docker-compose | — |
| Lenguaje | Python | 3.11 |

---

## 3. Arquitectura actual

```
[Usuario] --> [Streamlit Frontend :8501]
                        |
                   HTTP/REST
                        |
              [FastAPI Backend :8000]
                   |          |
          [SQLAlchemy]    [OpenAI API]
                   |
              [SQLite .db]
```

**Modulos implementados:**

- `app/adapters/` — Parsers de extractos bancarios. Banco Macro (.xls/.xlsx) y Banco Galicia (.xlsx). Deteccion automatica por estructura del archivo.
- `app/services/conciliation.py` — Motor de conciliacion: credito bancario → CUIT → facturas FIFO con tolerancia ±10%.
- `app/services/ingestion.py` — Ingesta de facturas desde Excel (hoja "pendientes") y upsert del padron de clientes.
- `app/routers/reclamos.py` — CRUD de reclamos con historial de respuestas, analisis IA (GPT-4o-mini), borrador de mail.
- `app/routers/conciliation.py` — Endpoints de dashboard: facturas vencidas, historial de conciliaciones, mail de cobro deterministico.
- `frontend/pages/` — 4 paginas Streamlit: Movimientos Bancarios, Conciliacion, Datos Maestros, Reclamos.

**Datos que maneja actualmente:**

| Tabla | Descripcion |
|-------|-------------|
| `facturas` | Nro, razon social, saldo, vencimiento, condicion de pago, estado |
| `padron` | CUIT, cliente_id, razon social, mails de contacto |
| `movimientos_banco` | Fecha, monto, concepto, CUIT extraido, banco origen |
| `conciliaciones` | Relacion movimiento → factura, monto aplicado, fecha |
| `reclamos` | Cliente, descripcion, historial de respuestas, estado, fechas |

---

## 4. Limitaciones actuales (deuda tecnica)

| Limitacion | Impacto |
|-----------|---------|
| SQLite como base de datos | No soporta escrituras concurrentes. Limite practico ~5 usuarios simultaneos. |
| Ingesta manual desde Excel | El area de administracion debe exportar del ERP y subir el archivo a mano. |
| Conciliacion solo 1:1 | Un credito bancario puede cancelar UNA sola factura. Pagos que agrupan varias facturas no se concilian automaticamente. |
| Sin workflow de aprobacion | Las conciliaciones se aplican automaticamente. No hay paso de revision antes de marcar facturas como pagas en el ERP. |
| Sin integracion con ERP | Los cambios de estado (factura pagada) deben actualizarse manualmente en el ERP. |
| Bancos soportados: solo 2 | Macro y Galicia. Cualquier otro banco requiere desarrollo de un nuevo adapter. |
| Telefono no disponible | El padron actual no incluye numero de telefono para contacto por SMS/WhatsApp. |
| Sin autenticacion | Cualquiera con acceso a la URL puede operar el sistema. |

---

## 5. Roadmap de evolucion por modulo

### 5.1 Integracion con ERP

El cliente probablemente tiene una de estas dos situaciones:

**Escenario A — El ERP tiene API REST**
Es la integracion ideal. Se construye un adaptador que consume los endpoints del ERP para leer facturas, actualizar estados y leer el padron. No requiere acceso a la base de datos del ERP.

**Escenario B — Solo acceso a base de datos SQL**
Se crea una capa de integracion que consulta directamente las tablas del ERP (lectura) y ejecuta updates o inserts en las tablas correspondientes (escritura). Requiere que el proveedor del ERP documente el esquema de base de datos o que el cliente proporcione acceso y ejemplos de datos.

**Lo que se debe integrar:**

| Operacion | Descripcion |
|-----------|-------------|
| Leer facturas pendientes | Importar periodicamente (o en tiempo real) las facturas emitidas con saldo > 0 |
| Actualizar factura a pagada | Cuando se aprueba una conciliacion, marcar la factura como cobrada en el ERP |
| Leer padron de clientes | Importar CUIT, razon social, condiciones de pago, datos de contacto |
| Actualizar padron | Si hay datos que el ERP no tiene (telefono de reclamo, mail secundario), poder escribirlos |
| Leer reclamos del ERP | Si el ERP registra reclamos de producto, importarlos para mostrar el warning en cobranzas |
| Actualizar estado de reclamo | Cuando se cierra un reclamo en este sistema, reflejarlo en el ERP |
| Obtener saldo facturado vencido | Suma de facturas vencidas con saldo pendiente (puede calcularse localmente) |

**Datos minimos del padron que el ERP debe proveer:**

| Campo | Requerido | Fuente sugerida |
|-------|-----------|-----------------|
| CUIT | Si | ERP |
| Razon social | Si | ERP |
| Cliente ID interno | Si | ERP |
| Condicion de pago | Si | ERP |
| Mail contacto financiero | Si | ERP o manual en este sistema |
| Mail reclamo de producto | Opcional | ERP o manual |
| Telefono de contacto | Si | ERP o manual |

**Patron de integracion recomendado (independiente del escenario):**

Se crea una capa abstracta `ERP Adapter` (igual al patron que ya existe para los bancos). Cada implementacion concreta puede ser API REST o SQL directo, sin que el resto del sistema lo note.

```
ERPAdapter (base)
    ├── ERPRestAdapter      (si tienen API)
    └── ERPSqlAdapter       (si solo tienen base SQL)
```

### 5.2 Motor de conciliacion — Modo Balance

El modo actual es **conciliacion directa**: un credito bancario se matchea contra una factura del mismo CUIT si el monto esta dentro del ±10%.

El modo nuevo es **conciliacion por balance**:

1. Cada credito bancario que ingresa se suma al balance del CUIT.
2. El sistema aplica el balance contra las facturas mas antiguas del CUIT (FIFO).
3. Si el balance cubre una factura completa, la cierra. Si cubre parcialmente, la actualiza.
4. El balance sobrante queda registrado y se aplica en la proxima ejecucion.
5. El area de administracion ve una cola de conciliaciones pendientes de aprobacion.
6. Aprueba de forma masiva o una por una.
7. Al aprobar, se dispara la actualizacion al ERP.

**Nueva tabla requerida:**

```sql
balance_cuit (
    id, cuit, saldo_disponible, fecha_ultimo_movimiento
)

conciliaciones_pendientes (
    id, movimiento_id, factura_id, monto_aplicado,
    modo (directa | balance), estado (pendiente | aprobada | rechazada),
    aprobado_por, fecha_aprobacion
)
```

**Reglas de negocio a definir con el cliente:**

- Que pasa si el balance de un CUIT acumula durante 60 dias sin matchear facturas (saldo en favor del cliente).
- Si se puede rechazar una conciliacion sugerida y asignarla manualmente a otra factura.
- Si una factura puede tener conciliaciones parciales de multiples creditos.

### 5.3 Gestion de facturas vencidas

Cambios sobre la implementacion actual:

- Agregar telefono al padron y mostrarlo en la tabla de vencidas.
- Boton "Enviar mail" dispara la generacion del mail deterministico que ya existe y abre el cliente de mail del usuario (mailto:) o llama a un servicio de envio (SendGrid/SES).
- Boton "Enviar WhatsApp" genera el link `wa.me/549XXXXXXXXXX?text=...` con el mensaje pre-armado.
- Dispatch masivo: seleccionar N clientes y disparar en bloque, con log de envios.
- El warning de reclamo de producto activo se mantiene y bloquea el envio masivo hasta que el usuario lo confirme explicitamente.

### 5.4 Gestion de reclamos

Cambios sobre la implementacion actual:

- Limitar tokens de IA: max_tokens=1500 por llamada, cache del prompt de sistema con la API de OpenAI (reduce costo ~50% en llamadas repetidas al mismo cliente).
- Mostrar costo estimado de la llamada antes de ejecutar (tokens de entrada * precio).
- Despues del plan de accion, boton "Responder por mail" (abre modal con borrador) y boton "Responder por telefono" (muestra numero y script sugerido).
- Historial de envios: registrar si se envio mail o se realizo llamada, con fecha y usuario.

### 5.5 Dashboard financiero con IA

Nuevo modulo. Componentes:

**KPIs estaticos (cargados al abrir la pagina):**
- Saldo total vencido por bucket de mora: 0-30 dias, 31-60, 61-90, +90.
- Facturas a vencer en los proximos 7, 15, 30 dias.
- Forecast de cobranza: suma de facturas con vencimiento en el mes actual.
- Facturacion real del mes: suma de facturas cobradas en el periodo.
- Top 10 clientes por deuda vencida.
- Distribucion por condicion de pago.

**Chat con IA en lenguaje natural:**

El usuario escribe una pregunta en texto libre. Un agente con acceso a herramientas (`tool_use`) decide si:
- Responde directamente con datos del contexto ya cargado.
- Genera y ejecuta una query SQL contra la base de datos local.
- Devuelve un DataFrame que se muestra como tabla.
- Ofrece exportar a Excel.

Ejemplos de preguntas que debe responder:
- "Cuales son los 5 clientes que mas deben?"
- "Quien tarda mas en pagar en promedio?"
- "Cuanto se cobro en abril?"
- "Hay alguna factura de mas de 90 dias sin contacto?"
- "Generame un Excel con todo lo vencido agrupado por cliente"

**Stack para el chat:**
- Modelo: gpt-4o-mini (suficiente para SQL generation) o claude-haiku-4-5 (mas economico en tokens).
- Patron: Text-to-SQL con validacion antes de ejecutar (no permitir DELETE/DROP).
- La respuesta puede ser texto, tabla Streamlit o archivo descargable.

### 5.6 Nuevos adapters de Home Banking

El patron actual de `BankAdapter` es correcto y extensible. Para cada nuevo banco se implementa una clase que hereda de `BankAdapter` y sobreescribe `parse()`.

Para bancos desconocidos, se propone un **adapter generico con IA**:

1. El usuario sube el archivo.
2. El sistema no reconoce el formato.
3. Se muestra la pantalla "Banco no reconocido".
4. El usuario puede completar un formulario indicando: columna de fecha, columna de monto, columna de concepto.
5. El sistema guarda esa configuracion como un nuevo "perfil de banco" reutilizable.
6. Opcionalmente, un agente IA analiza las primeras filas del archivo y sugiere el mapeo de columnas.

Esto evita tener que hacer un deploy por cada nuevo banco.

---

## 6. Stack objetivo (produccion en AWS)

| Capa | Tecnologia actual | Tecnologia objetivo | Razon |
|------|------------------|--------------------|----|
| Base de datos | SQLite | PostgreSQL (RDS) | Concurrencia, backups automaticos, escalabilidad |
| Backend | FastAPI (local) | FastAPI en ECS Fargate o EC2 | Alta disponibilidad, escalado automatico |
| Frontend | Streamlit (local) | Streamlit en ECS Fargate | Mismo stack, solo cambia donde corre |
| Cola de tareas | Ninguna | Celery + SQS | Para procesar conciliaciones masivas en background |
| Storage de archivos | Disco local | S3 | Almacenar Excel subidos, logs, exports |
| IA | OpenAI API | OpenAI API o Amazon Bedrock | Bedrock si el cliente prefiere no salir de AWS |
| Auth | Ninguna | Cognito o Auth0 | Autenticacion con MFA para acceso al sistema |
| CI/CD | Manual (git push) | GitHub Actions + ECR | Deploy automatico en cada push a main |

**Por que no un LLM propio en AWS:**
Correr un modelo de lenguaje propio (ej. Llama en EC2 GPU) cuesta entre USD 300 y 2000/mes en compute, mas mantenimiento. Usar la API de OpenAI o Amazon Bedrock (Claude) tiene costo variable por uso, tipicamente entre USD 10-80/mes para el volumen de una Pyme. La opcion API es la correcta.

**Costo estimado AWS (produccion basica):**

| Servicio | Uso | Costo estimado/mes |
|----------|-----|-------------------|
| RDS PostgreSQL t3.micro | DB principal | USD 25 |
| ECS Fargate (API + Frontend) | 0.5 vCPU, 1GB RAM cada uno | USD 30 |
| S3 | Archivos subidos | USD 5 |
| OpenAI API | ~500 llamadas/mes | USD 15-40 |
| Total estimado | | USD 75-100/mes |

---

## 7. Autenticacion y seguridad (pendiente)

El sistema actual no tiene autenticacion. Antes de cualquier deploy en la nube se debe agregar:

- Login con usuario y password.
- Roles: administrador (acceso total), operador (solo carga y conciliacion), solo lectura (dashboard).
- Todas las llamadas a la API deben requerir un token JWT.
- El `.env` con claves de API nunca debe commitarse (ya esta en `.gitignore`).
