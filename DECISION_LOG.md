# Bitácora de decisiones

## 1. Streamlit como superficie operativa

Se mantiene Streamlit por velocidad de entrega, pero la interfaz se reorganizó alrededor de registrar, filtrar, abrir expediente y asignar recursos.

## 2. Honduras como dominio explícito

Se reemplazaron distritos inventados por Tegucigalpa, San Pedro Sula y La Ceiba. `city_id` es la clave de partición de Kafka y MongoDB conserva índices por ciudad, estado y prioridad.

## 3. La cola es un flujo de trabajo

La consulta usa filtros y `count_documents`, ordenamiento por prioridad o fecha, `skip/limit` y páginas de 25/50/100. No está limitada a los primeros 15 o 40 reportes.

## 4. Despacho multiunidad

`assigned_units` es una lista, no un campo singular. El expediente puede despachar varias unidades de cuatro tipos y deja el estado visible en cuatro pasos.

## 5. Kafka permanece detrás de la interfaz

El operador solo ve “Registrar y poner en cola”. Productor idempotente con `acks=all`, consumidor con confirmación manual y MongoDB deduplicando por `report_number`.

## 6. Datos masivos

Se conservan escenarios, throughput, duplicados y malformados para demostrar validación y dead letters sin contaminar el flujo individual.

