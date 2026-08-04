# Bitácora de decisiones técnicas

## 1. Streamlit como aplicación web

**Decisión:** usar Streamlit para el generador y el dashboard.

**Razón:** permite construir una interfaz web íntegramente en Python y reducir el tiempo de integración. El equipo puede explicar el código sin mantener dos proyectos separados.

**Alternativa descartada:** React con FastAPI. Ofrece mayor libertad visual, pero aumenta el número de componentes, dependencias y puntos de fallo para una demostración académica corta.

## 2. Un topic particionado por distrito

**Decisión:** usar el topic `emergency-calls` con seis particiones y `district_id` como clave.

**Razón:** mantiene el orden relativo de cada distrito y permite procesar distritos diferentes en paralelo. También facilita agregar consumidores dentro del mismo grupo.

**Alternativa descartada:** un topic por distrito. Aumenta la administración de topics y dificulta incorporar nuevos distritos.

## 3. Tres brokers en modo KRaft

**Decisión:** usar tres brokers/controladores Kafka, replicación 3 y mínimo de dos réplicas sincronizadas.

**Razón:** permite explicar disponibilidad y tolerancia a la pérdida de un broker sin depender de ZooKeeper.

**Trade-off:** utiliza más memoria que un broker único, pero representa mejor una arquitectura distribuida.

## 4. Productor idempotente

**Decisión:** configurar `enable.idempotence=true` y `acks=all`.

**Razón:** reduce duplicados causados por reintentos y confirma la escritura en las réplicas sincronizadas.

**Trade-off:** la confirmación completa puede añadir latencia frente a `acks=1`.

## 5. Semántica de procesamiento al menos una vez

**Decisión:** desactivar el auto-commit y confirmar el offset después de almacenar cada evento.

**Razón:** si el consumidor falla antes de guardar, Kafka vuelve a entregar el evento.

**Consecuencia:** un evento puede repetirse. Se controla con un índice único sobre `report_number`, por lo que el consumidor es idempotente.

## 6. MongoDB como almacenamiento documental

**Decisión:** almacenar eventos y métricas en MongoDB.

**Razón:** los eventos JSON pueden evolucionar sin migraciones rígidas y MongoDB permite índices, agregaciones y escritura de documentos a gran volumen.

**Alternativa descartada:** SQLite. Es excelente para un prototipo local, pero su escritura concurrente y escalabilidad son más limitadas para el escenario masivo propuesto.

## 7. Datos realistas y no uniformes

**Decisión:** aplicar pesos distintos por distrito y tipo, prioridades condicionadas y escenarios de operación normal, accidente múltiple, tormenta severa y evento masivo.

**Razón:** una distribución uniforme sería fácil de generar, pero poco realista. El Distrito Centro recibe más eventos y los incendios o rescates tienen mayor probabilidad de prioridad alta.

## 8. Imperfecciones controladas

**Decisión:** permitir entre 0% y 10% de duplicados o eventos incompletos desde la interfaz.

**Razón:** demuestra limpieza de datos. Los duplicados se omiten y los malformados se guardan en `dead_letters` para auditoría.

## 9. Balance de carga

**Decisión:** calcular `unidades disponibles - llamadas activas` y complementar con la razón `llamadas / unidades`.

**Razón:** el balance absoluto indica déficit o capacidad, mientras la razón permite comparar distritos de tamaños diferentes.

## 10. Alcance de la demostración

**Decisión:** no implementar telefonía real, geolocalización, integración con ambulancias ni identidad ciudadana.

**Razón:** el proyecto evalúa la infraestructura de datos que alimenta y comprende la central, no la operación real del servicio 911.
