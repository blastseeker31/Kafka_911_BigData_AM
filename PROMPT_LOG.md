# Bitácora de prompts utilizados

## Prompt 1 - Conceptualización

> Estoy desarrollando como proyecto final de Big Data un sistema de streaming con interfaz gráfica utilizando Apache Kafka y Python. El dominio será una central simulada de emergencias 911. Ayúdame a plantear el alcance, los datos de cada emergencia, los wireframes y la arquitectura inicial.

## Prompt 2 - Arquitectura

> Adapta el sistema 911 al formato de arquitectura visto en clase. Debe mostrar un productor Python, un broker Kafka, un consumidor, almacenamiento y un dashboard. Indica qué componente publica, consume, guarda y consulta.

## Prompt 3 - Frontend

> Construye únicamente el frontend en Streamlit a partir de los wireframes: login, centro de control y detalle de emergencia. Usa datos simulados, permite registrar llamadas, navegar al expediente, asignar una unidad y actualizar estados. No conectes todavía Kafka ni la base de datos.

## Prompt 4 - Integración completa según la asignación

> Revisa el documento oficial del Proyecto Integrador de Big Data y convierte el prototipo en un MVP funcional. Implementa generación individual y masiva con variabilidad e imperfecciones controladas, mide throughput, publica los eventos JSON en Kafka, particiona por distrito, procesa con un consumidor Python, valida y deduplica, almacena en una base documental y muestra el balance de carga por distrito. Conserva las tres pantallas definidas. Incluye Docker Compose, pruebas, README, diagrama, bitácora de decisiones y guion de defensa. Prioriza una demostración reproducible y un código que podamos explicar.

## Prompt 5 - Validación

> Ejecuta pruebas del generador, la validación y el cálculo del balance. Revisa la configuración de Docker, confirma que todos los componentes tengan variables coherentes y prepara una secuencia de demostración que muestre una llamada individual, un pico masivo, throughput, datos inválidos y balance por distrito.

