# Registro de decisiones y dirección del proyecto

Este documento resume cómo dirigí el desarrollo del sistema. Las instrucciones parten del problema operativo y de las decisiones de arquitectura; la implementación debía seguir ese criterio y no terminar en una maqueta genérica.

## 1. Definí el problema y el resultado esperado

> Quiero convertir el MVP en una central de despacho útil para Honduras. El operador debe poder registrar, priorizar y despachar una emergencia crítica en menos de 15 segundos. La interfaz debe ser clara, blanca, profesional y enfocada en la acción.

También definí desde el inicio que no quería un dashboard escolar: el flujo debía servir para atender reportes, no solo para mostrar métricas.

## 2. Fijé el dominio hondureño

> El sistema debe trabajar con Tegucigalpa, San Pedro Sula y La Ceiba. No usar distritos inventados. Cada reporte debe incluir ciudad, colonia o referencia, ubicación, tipo, prioridad, descripción y personas en riesgo.

Esta decisión se refleja en el modelo de eventos, los datos generados, los filtros, las métricas y la clave de partición de Kafka: `city_id`.

## 3. Elegí las tecnologías por su función

> Mantener Streamlit para entregar la interfaz en Python, Kafka para desacoplar la recepción del procesamiento y MongoDB para guardar documentos de emergencia y métricas operativas.

La elección no fue solo por conveniencia:

- Streamlit permite concentrar el MVP en Python y avanzar rápido en el flujo operativo.
- Kafka funciona como buffer durable durante picos de llamadas y permite procesar los eventos de forma independiente.
- MongoDB encaja con eventos JSON que pueden evolucionar y permite índices, filtros, paginación y agregaciones.
- Docker Compose hace reproducible el entorno completo: tres brokers Kafka, MongoDB, consumidor y aplicación.

## 4. Diseñé el flujo de atención

> El formulario debe mostrar los campos mínimos, hacer evidente la prioridad y tener una acción principal clara. Al abrir un reporte, el operador debe poder asignar varias unidades simultáneamente.

Por eso se implementaron:

- Estados Nuevo, Despachado, En atención y Cerrado.
- Lista `assigned_units` en vez de una sola unidad.
- Tipos de recurso: ambulancia, patrulla, bomberos y rescate.
- Expediente con información de ubicación, personas en riesgo, observaciones e historial de estado.

## 5. Pedí una cola que realmente escale

> La cola debe soportar más de 1,500 reportes. Necesito búsqueda, filtros por ciudad, tipo, prioridad y estado, ordenamiento y paginación real.

La implementación usa índices de MongoDB, `count_documents`, `skip`, `limit` y ordenamiento por prioridad o fecha. La interfaz no se queda limitada a los primeros 15 o 40 registros.

## 6. Conservé la infraestructura de Big Data

> Kafka, generación individual y masiva, consumidor, deduplicación, dead letters y métricas deben mantenerse, pero deben quedar detrás de un flujo que tenga sentido para el operador.

El productor usa `acks=all` e idempotencia. El consumidor valida antes de confirmar el offset. MongoDB usa un índice único en `report_number` para que una reentrega no genere un duplicado.

## 7. Diseñé la demostración

> La grabación debe mostrar un caso individual de prioridad crítica, despacho de varias unidades, cambio de estado, resumen por ciudad y un lote masivo de 1,500 reportes.

La pantalla **Generación masiva** conserva escenarios, throughput e imperfecciones controladas. También incluye el borrado de datos de prueba para poder repetir el runthrough desde cero.

## 8. Criterio de validación

> Antes de entregar, compilar el código, ejecutar las pruebas, levantar Docker, verificar la interfaz y documentar lo que realmente se probó.

Las comprobaciones disponibles son:

- `pytest -q` para generador y validación.
- `python -m compileall -q src tests` para sintaxis.
- `docker compose ps` para servicios.
- Logs de `app` y `consumer`.
- Recorrido manual en `http://localhost:8501`.

