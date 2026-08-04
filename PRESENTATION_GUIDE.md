# Guion de exposición y demostración

## Apertura

> Nuestro proyecto no intenta reemplazar una central 911 real. Construimos la infraestructura de datos que permite recibir, procesar y comprender miles de llamadas en tiempo real. El problema principal es conocer el balance entre las llamadas activas y las unidades disponibles por distrito.

## Arquitectura

> El flujo comienza en una aplicación web desarrollada con Streamlit. Desde ella podemos registrar una llamada individual o simular un pico de miles de llamadas. Cada llamada se convierte en JSON y se publica en el topic `emergency-calls`.

> El topic tiene seis particiones y utilizamos el distrito como clave. Esto conserva el orden dentro de cada distrito y permite que diferentes distritos se procesen en paralelo. Kafka corre en tres brokers KRaft con replicación tres.

> Un consumidor Python valida los eventos. Los duplicados se detectan mediante el número de reporte y los eventos incompletos van a una colección de dead letters. Los válidos se guardan en MongoDB y actualizan las métricas por distrito.

## Demostración en vivo

1. Entrar con `Alejandro / 911`.
2. Mostrar los indicadores del centro de control.
3. Registrar una emergencia individual con prioridad 5.
4. Abrir el expediente, asignar una ambulancia y cambiarla a **En camino**.
5. Ir al generador masivo.
6. Generar 1,000 llamadas con 2% de imperfecciones.
7. Mostrar el throughput medido por el sistema.
8. Mostrar cómo aumentan eventos procesados y rechazados.
9. Abrir el balance por distrito y seleccionar el que indique el profesor.

## Cómo explicar el balance

> El balance se calcula restando las llamadas activas a las unidades disponibles. Un número negativo significa déficit. Además calculamos la razón de carga. Menos de 0.60 es estable, de 0.60 a 1 requiere atención y mayor que 1 representa exposición crítica.

## Preguntas probables

### ¿Por qué un topic y no uno por distrito?

> Porque el distrito se utiliza como clave de partición. Obtenemos paralelismo y orden por distrito sin multiplicar la administración de topics.

### ¿Qué es un offset?

> Es la posición de un evento dentro de una partición. El consumidor confirma el offset después de almacenar el evento, por lo que una falla anterior provoca que Kafka lo entregue nuevamente.

### ¿Cómo manejan los duplicados?

> Usamos semántica al menos una vez y un índice único sobre `report_number`. Si Kafka reentrega un evento, MongoDB rechaza la segunda inserción y las métricas no vuelven a incrementarse.

### ¿Por qué MongoDB?

> Porque los eventos llegan como documentos JSON, pueden variar con el tiempo y el escenario plantea volumen y variedad. SQLite habría sido más sencillo, pero menos apropiado para escritura concurrente y escalabilidad.

### ¿Cómo soporta la caída de un broker?

> Cada partición se replica tres veces y el productor exige confirmación de las réplicas sincronizadas. Con dos réplicas disponibles, el clúster puede continuar aunque un broker falle.

### ¿Qué ocurre durante un pico?

> Kafka actúa como buffer duradero. El productor puede publicar más rápido que el consumidor, y los eventos permanecen en las particiones hasta que el grupo consumidor los procese.

### ¿Qué cambiaríamos para producción?

> Separaríamos brokers y MongoDB en servidores distintos, añadiríamos autenticación real, TLS, monitoreo, más consumidores, réplicas de MongoDB y políticas de retención.

## Cierre

> La solución demuestra captura masiva, ingesta distribuida, procesamiento, limpieza, almacenamiento documental y visualización. La herramienta de IA ayudó a escribir y revisar el código, pero las decisiones técnicas, sus alternativas y sus consecuencias están documentadas y podemos defenderlas.

