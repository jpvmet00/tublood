# Dudas de Integracion y Ejemplos de Datos Requeridos

Este documento lista las preguntas que hay que responder antes de disenar la integracion con el ERP, junto con los ejemplos de tablas y datos que se necesitan para comenzar el desarrollo.

---

## Bloque 1 — Tipo de integracion disponible

Estas preguntas determinan cuanto tiempo toma la integracion y que arquitectura usar.

| # | Pregunta | Por que importa |
|---|---------|-----------------|
| 1 | El ERP tiene API REST disponible? Si la tiene, hay documentacion o Swagger? | Define si usamos HTTP o SQL directo |
| 2 | Si no hay API, se puede dar acceso de lectura/escritura a la base de datos del ERP? Con que motor? (SQL Server, MySQL, PostgreSQL, Oracle) | Define el tipo de driver de conexion |
| 3 | El ERP esta en la nube o es on-premise (servidor en la empresa)? | Afecta la conectividad desde AWS |
| 4 | Si es on-premise, hay VPN o IP publica con puerto abierto desde donde se pueda conectar? | Requisito de red para integracion remota |
| 5 | Con que frecuencia cambian las facturas pendientes durante el dia? (tiempo real, cada hora, una vez por dia) | Define si la sincronizacion es por webhook, polling o batch nocturno |
| 6 | El ERP es un producto comercial (SAP, Tango, Bejerman, Flexxus, A3, etc.) o es desarrollo a medida? | Si es comercial puede haber integraciones ya existentes |

---

## Bloque 2 — Datos de facturas

Se necesita entender que informacion existe en el ERP sobre facturas para saber que se puede traer automaticamente y que hay que completar manualmente.

**Preguntas:**

| # | Pregunta |
|---|---------|
| 7 | Hay un campo de CUIT del cliente en cada factura? |
| 8 | Las facturas tienen un numero unico que no cambia? (numero de comprobante, numero interno) |
| 9 | Hay campo de "condicion de venta" o "condicion de pago"? Que valores puede tomar? (contado, 30 dias, 60 dias, etc.) |
| 10 | El saldo pendiente por factura se calcula en el ERP o hay que calcularlo como (monto - cobros aplicados)? |
| 11 | Cuando una factura se cobra parcialmente, el ERP lo registra? Hay un campo de "saldo pendiente" o solo "monto total"? |
| 12 | Hay facturas de diferentes tipos (A, B, C, M, E)? El tipo afecta la logica de cobro? |
| 13 | Se puede filtrar por estado de factura (pendiente, parcialmente pagada, cobrada, anulada)? |

**Ejemplo de estructura minima requerida:**

```
facturas_pendientes
├── nro_factura        VARCHAR   -- "F-001-00001234", unico
├── tipo_comprobante   VARCHAR   -- "A", "B", "C"
├── cuit_cliente       VARCHAR   -- "30-71719902-0" o "30717199020"
├── cliente_id         VARCHAR   -- ID interno del cliente en el ERP
├── razon_social       VARCHAR   -- "Instituto Data Science SRL"
├── fecha_emision      DATE      -- 2026-01-15
├── fecha_vencimiento  DATE      -- 2026-02-14
├── condicion_venta    VARCHAR   -- "30 dias", "contado", "60/90"
├── monto_total        DECIMAL   -- 150000.00
├── monto_cobrado      DECIMAL   -- 0.00 (o campo de saldo si existe)
└── estado             VARCHAR   -- "pendiente", "cobrada", "anulada"
```

**Ejemplo de filas:**

| nro_factura | cuit_cliente | razon_social | fecha_vencimiento | monto_total | monto_cobrado | estado |
|-------------|-------------|--------------|-------------------|-------------|---------------|--------|
| FA-001-00001234 | 30717199020 | Instituto Data Science SRL | 2026-03-15 | 150000.00 | 0.00 | pendiente |
| FA-001-00001235 | 30716132028 | LocalPayment SA | 2026-02-10 | 87500.00 | 87500.00 | cobrada |
| FA-001-00001236 | 30717199020 | Instituto Data Science SRL | 2026-01-20 | 62000.00 | 30000.00 | parcial |

---

## Bloque 3 — Datos del padron de clientes

**Preguntas:**

| # | Pregunta |
|---|---------|
| 14 | El ERP tiene tabla de clientes con CUIT? |
| 15 | Hay campo de razon social, condicion de pago habitual, limite de credito? |
| 16 | Hay algun campo de contacto (mail, telefono)? Si hay varios contactos por cliente, como estan guardados? |
| 17 | Hay un campo para distinguir el tipo de cliente? (hospital publico, clinica privada, distribuidor, etc.) |
| 18 | Los clientes tienen un ID unico en el ERP? Es el mismo que se usa internamente en TUBLOOD? |

**Ejemplo de estructura minima requerida:**

```
clientes
├── cliente_id              VARCHAR   -- ID interno del ERP
├── cuit                    VARCHAR   -- "30717199020"
├── razon_social            VARCHAR   -- "Instituto Data Science SRL"
├── condicion_pago          VARCHAR   -- "30 dias neto"
├── limite_credito          DECIMAL   -- 500000.00 (opcional)
├── mail_contacto           VARCHAR   -- "admin@cliente.com"
├── mail_reclamo_financiero VARCHAR   -- puede ser nulo, se completa en este sistema
├── mail_reclamo_producto   VARCHAR   -- puede ser nulo, se completa en este sistema
├── telefono_contacto       VARCHAR   -- "+54 9 11 1234-5678"
└── activo                  BOOLEAN   -- true/false
```

**Datos que pueden no estar en el ERP y se completarian en este sistema:**
- `mail_reclamo_financiero` — mail especifico para envios de deuda vencida
- `mail_reclamo_producto` — mail del area tecnica para reclamos de producto
- `telefono_contacto` — para WhatsApp

---

## Bloque 4 — Reclamos

**Preguntas:**

| # | Pregunta |
|---|---------|
| 19 | El ERP registra reclamos de producto o de servicio? |
| 20 | Si los registra, tienen estados (abierto, en proceso, cerrado)? |
| 21 | Los reclamos estan asociados al cliente (CUIT o cliente_id)? |
| 22 | Hay historial de respuestas o solo el estado actual? |
| 23 | Se puede escribir en la tabla de reclamos del ERP para actualizar el estado? |

**Ejemplo de estructura de reclamos del ERP (si existe):**

```
reclamos_erp
├── reclamo_id     VARCHAR
├── cliente_id     VARCHAR
├── tipo           VARCHAR   -- "producto", "facturacion", "entrega"
├── descripcion    TEXT
├── estado         VARCHAR   -- "abierto", "en_proceso", "cerrado"
├── fecha_apertura DATE
└── fecha_cierre   DATE
```

---

## Bloque 5 — Extractos bancarios

**Preguntas:**

| # | Pregunta |
|---|---------|
| 24 | Ademas de Banco Macro y Banco Galicia, hay otros bancos con los que opera TUBLOOD? |
| 25 | Para los bancos actuales: con que frecuencia se bajan los extractos? (diario, semanal, cuando hay pagos) |
| 26 | El extracto de cada banco puede bajarse por API del banco o solo se descarga el archivo desde el homebanking manualmente? |
| 27 | Los depositos de clientes vienen con el CUIT en el campo "concepto"? O viene otra informacion? |
| 28 | Hay transferencias CBU a CBU donde no viene el CUIT? Como se identifican hoy esos pagos? |

**Ejemplo de fila de un extracto donde el CUIT NO viene en el concepto:**

```
fecha       | monto     | concepto
2026-03-10  | 150000.00 | "TRANSF BANCO MACRO OPERACION 8832910 CTAS PROP"
```

Para este caso hay que definir una regla de fallback: mostrar al usuario para asignacion manual, o intentar cruzar por monto contra facturas pendientes del dia.

---

## Bloque 6 — Flujo de aprobacion de conciliaciones

**Preguntas:**

| # | Pregunta |
|---|---------|
| 29 | Quien aprueba que una factura quedo pagada? (una persona, varias, cualquier usuario del sistema) |
| 30 | Hay un paso de revision contable antes de cerrar una factura en el ERP? |
| 31 | Si una conciliacion se aprueba por error, hay un proceso para revertirla? |
| 32 | Cuantos usuarios van a usar el sistema de forma concurrente? |

---

## Checklist de datos a solicitar al cliente

Para comenzar el desarrollo de la integracion se necesitan:

- [ ] Confirmacion del tipo de ERP (nombre del producto o si es a medida)
- [ ] Si hay API: URL base de la API, documentacion o Swagger, credenciales de prueba
- [ ] Si hay base de datos: tipo de motor, credenciales de acceso a un ambiente de testing, nombre de las tablas de facturas y clientes
- [ ] Exportacion de ejemplo de facturas pendientes (puede ser Excel anonimizado, solo para ver la estructura)
- [ ] Exportacion de ejemplo del padron de clientes (puede ser anonimizado)
- [ ] Un extracto bancario real de Macro y uno de Galicia de los ultimos 30 dias (para validar los parsers actuales con datos reales)
- [ ] Lista de todos los bancos con los que opera TUBLOOD actualmente
- [ ] Confirmacion de si los reclamos de producto se registran en el ERP y si hay acceso a esos datos
