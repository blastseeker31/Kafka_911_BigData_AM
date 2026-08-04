# Guion de grabación · Central 911 Honduras

## Video recomendado (3–4 minutos)

1. Abrir `http://localhost:8501` y entrar con `Alejandro / 911`. Mostrar que el login cabe completo en el viewport.
2. Registrar una Emergencia médica en Tegucigalpa, colonia Kennedy, ubicación concreta, prioridad 5, 2 personas en riesgo y descripción breve.
3. Pulsar **Registrar y poner en cola**. Explicar que Kafka procesa el reporte detrás de la interfaz.
4. Abrir el expediente y seleccionar al mismo tiempo una ambulancia, una patrulla, bomberos y rescate. Cambiar a **Despachado**.
5. Cambiar a **En atención** y mostrar nuevos, críticos, unidades disponibles y ocupadas.
6. Abrir **Resumen por ciudad** para explicar la presión de las tres ciudades.
7. En **Generación masiva**, generar 1,500 reportes con 2% de imperfecciones y mostrar throughput.
8. Volver a la cola: usar búsqueda, filtros, ordenar por prioridad y pasar de página.

## Explicación técnica

Kafka tiene seis particiones y tres brokers KRaft. El productor usa `acks=all` e idempotencia. El consumidor valida, manda malformados a dead letters y confirma el offset después de insertar. MongoDB tiene un índice único en `report_number`.

## Cierre

“El cambio principal no es solo visual: una emergencia crítica pasa de reporte a despacho multiunidad en segundos, mientras Kafka, validación, deduplicación y métricas trabajan detrás del flujo.”

