from __future__ import annotations

import json
import logging
import signal
from typing import Any

from confluent_kafka import Consumer, KafkaError, KafkaException

from src.config import settings
from src.processor import validate_event
from src.storage import EmergencyStorage


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("911-consumer")
RUNNING = True


def stop_consumer(_signum: int, _frame: Any) -> None:
    global RUNNING
    RUNNING = False


def main() -> None:
    signal.signal(signal.SIGTERM, stop_consumer)
    signal.signal(signal.SIGINT, stop_consumer)
    storage = EmergencyStorage()
    consumer = Consumer(
        {
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "group.id": settings.kafka_group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
            "client.id": "central-911-processor",
        }
    )
    consumer.subscribe([settings.kafka_topic])
    LOGGER.info("Consumidor conectado al topic %s", settings.kafka_topic)

    try:
        while RUNNING:
            message = consumer.poll(1.0)
            if message is None:
                continue
            if message.error():
                if message.error().code() == KafkaError._PARTITION_EOF:
                    continue
                raise KafkaException(message.error())

            try:
                event = json.loads(message.value().decode("utf-8"))
                errors = validate_event(event)
                if errors:
                    storage.save_dead_letter(event, errors)
                    LOGGER.warning("Evento inválido enviado a dead letters: %s", errors)
                else:
                    inserted = storage.save_valid_event(event)
                    if not inserted:
                        LOGGER.info("Duplicado ignorado: %s", event.get("report_number"))
                consumer.commit(message=message, asynchronous=False)
            except Exception:
                LOGGER.exception("No se pudo procesar el evento; no se confirma el offset")
    finally:
        consumer.close()
        LOGGER.info("Consumidor detenido")


if __name__ == "__main__":
    main()

