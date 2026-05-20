# Propuesta Comercial — Sistema de Gestion de Cobranzas TUBLOOD

## El problema

Toda empresa que vende a credito enfrenta la misma friccion operativa: los pagos llegan al banco, pero cruzarlos con las facturas correctas es un trabajo manual, lento y propenso a errores.

Para TUBLOOD SA esto se traduce en:

- Horas por semana del area de administracion cruzando extractos bancarios contra planillas de facturas.
- Facturas vencidas sin seguimiento sistematico, dependiendo de la memoria del equipo.
- Sin visibilidad en tiempo real de cuanto se debe cobrar, quien debe hace mas tiempo y que se hizo al respecto.
- Riesgo de contactar a un cliente por deuda cuando hay un reclamo de producto abierto, generando conflictos innecesarios.

---

## La solucion

Un sistema web centralizado que automatiza el ciclo completo de cobranza:

**Desde que se emite una factura hasta que el pago se acredita y se registra en el ERP, sin intervenciones manuales en el camino.**

El sistema se conecta con el ERP de TUBLOOD para obtener las facturas pendientes y actualizar los estados de pago. Ingiere automaticamente los extractos de los bancos que usa la empresa. Concilia creditos con facturas. Gestiona el seguimiento de deuda vencida. Mantiene el historial de reclamos y usa inteligencia artificial para apoyar la toma de decisiones del equipo.

---

## Funcionalidades

### 1. Conciliacion automatica de pagos

El sistema importa los movimientos de los home banking (Banco Macro y Banco Galicia, con posibilidad de agregar otros) y los cruza automaticamente contra las facturas pendientes de cada cliente.

La conciliacion puede ocurrir de dos formas:

**Conciliacion directa:** un pago corresponde a una factura especifica. El sistema lo detecta por monto y CUIT del cliente con una tolerancia configurable (por defecto 10%) para absorber diferencias por retenciones o redondeos.

**Conciliacion por balance:** un cliente realiza un pago que cubre varias facturas a la vez. El sistema acumula el credito y lo distribuye automaticamente contra las facturas mas antiguas hasta agotar el monto. El saldo sobrante queda registrado para el proximo pago.

En ambos casos, el equipo de administracion puede revisar las conciliaciones sugeridas y aprobarlas de forma masiva o una por una antes de que impacten en el ERP.

### 2. Gestion de facturas vencidas

Vista centralizada de todas las facturas con saldo pendiente vencido, con filtros por dias de mora, cliente y condicion de pago.

Desde esa vista el equipo puede, con un solo click:

- Generar y enviar un mail de solicitud de pago con el detalle de las facturas vencidas del cliente.
- Enviar un mensaje de WhatsApp al numero de contacto registrado.
- Disparar los contactos de forma masiva para N clientes en un solo paso.
- Ver una advertencia automatica si el cliente tiene un reclamo de producto abierto, evitando contactos inapropiados.

### 3. Gestion de reclamos

Registro completo de reclamos de clientes con historial de interacciones, estado (abierto/cerrado) y tiempo de resolucion.

Un agente de inteligencia artificial analiza el historial del reclamo y el comportamiento de pago del cliente para generar:

- Un plan de accion sugerido para el equipo.
- Un borrador de mail listo para enviar.
- Un script sugerido para contacto telefonico.

El sistema registra cada interaccion (mail enviado, llamada realizada) para que el historial sea completo y auditabie.

### 4. Dashboard financiero ejecutivo

Panel de indicadores clave en tiempo real:

- Saldo total vencido, desglosado por bucket de mora (0-30 dias, 31-60, 61-90, mas de 90).
- Facturas proximas a vencer (proximos 7, 15, 30 dias).
- Forecast de cobranza del mes: cuanto se espera cobrar segun los vencimientos del periodo.
- Facturacion real cobrada en el mes.
- Ranking de clientes por deuda vencida.
- Comportamiento historico de pagos por cliente.

Ademas, un **chat con inteligencia artificial** permite hacer preguntas en lenguaje natural y obtener respuestas con datos reales:

- "Cuales son los 5 clientes que mas deben?"
- "Quien tarda mas en pagar en promedio?"
- "Cuanto se cobro el mes pasado?"
- "Hay facturas de mas de 90 dias sin ningun contacto registrado?"
- "Generame un Excel con el detalle de todo lo vencido por cliente."

### 5. Integracion con el ERP

El sistema se conecta con el ERP de TUBLOOD para:

- Importar automaticamente las facturas pendientes (sin necesidad de exportar Excel).
- Actualizar el estado de una factura a "pagada" cuando se aprueba una conciliacion.
- Importar el padron de clientes con sus datos de contacto.
- Sincronizar el estado de reclamos.

La integracion es transparente para el usuario: los datos siempre estan actualizados sin intervenciones manuales.

Si el ERP no provee ciertos datos (telefono de contacto, mail de reclamo financiero), el sistema permite completarlos manualmente y los mantiene sincronizados.

### 6. Soporte para multiples bancos

Ademas de Banco Macro y Banco Galicia, el sistema incluye un **modulo de configuracion de bancos** que permite parametrizar el formato de un nuevo extracto bancario sin necesidad de desarrollo. El equipo tecnico completa un formulario indicando las columnas relevantes del archivo y el sistema aprende el formato.

---

## Como se implementa

### Fase 1 — Sistema operativo (ya implementado)
Carga manual de facturas y padron desde Excel. Ingesta de extractos de Macro y Galicia. Conciliacion directa. Gestion de reclamos con IA. Dashboard basico.

### Fase 2 — Integracion ERP y conciliacion avanzada
Conexion al ERP para importacion automatica de facturas y actualizacion de estados. Motor de conciliacion por balance. Workflow de aprobacion antes de impactar el ERP.

### Fase 3 — Comunicaciones y dashboard ejecutivo
Envio de mails y WhatsApp desde el sistema. Dashboard financiero completo. Chat con IA en lenguaje natural. Exportacion de reportes a Excel.

### Fase 4 — Produccion en la nube y seguridad
Deploy en AWS con alta disponibilidad. Login con roles y permisos. Soporte para multiples bancos con configuracion parametrica. Backups automaticos.

---

## Diferenciadores

**Especifico para el negocio de TUBLOOD:** no es un sistema generico. La logica de conciliacion, los tipos de reclamo, los datos del padron y el lenguaje de la interfaz estan adaptados a la operacion de una empresa de insumos medicos con venta a credito.

**Sin dependencia de herramientas externas para operar:** el equipo de administracion no necesita salir del sistema para hacer seguimiento de cobranzas. Mail, WhatsApp, historial de reclamos y aprobacion de pagos estan integrados.

**IA como asistente, no como reemplazo:** el sistema usa inteligencia artificial para sugerir acciones, redactar comunicaciones y responder preguntas sobre los datos. La decision final siempre la toma el equipo.

**Escalable desde el dia uno:** el sistema esta construido para crecer. Agregar un nuevo banco, conectar un nuevo ERP o incorporar nuevas funcionalidades no requiere reescribir lo que ya funciona.
