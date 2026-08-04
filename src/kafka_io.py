from __future__ import annotations

import json
import time
from typing import Any, Iterable

from confluent_kafka import Producer

from src.config import settings


class EmergencyProducer:
    def __init__(self) -> None:
        self.producer = Producer(
            {
                "bootstrap.servers": settings.kafka_bootstrap_servers,
                "client.id": "central-911-web-generator",
                "acks": "all",
                "enable.idempotence": True,
                "compression.type": "snappy",
                "linger.ms": 5,
                "batch.size": 65536,
            }
        )

    def publish_many(self, events: Iterable[dict[str, Any]]) -> dict[str, Any]:
        counters = {"delivered": 0, "errors": 0}

        def delivery_report(error: object, _message: object) -> None:
            if error:
                counters["errors"] += 1
            else:
                counters["delivered"] += 1

        started = time.perf_counter()
        queued = 0
        for event in events:
            while True:
                try:
                    self.producer.produce(
                        settings.kafka_topic,
                        key=str(event.get("district_id", "unknown")),
                        value=json.dumps(event, ensure_ascii=False).encode("utf-8"),
                        callback=delivery_report,
                    )
                    queued += 1
                    break
                except BufferError:
                    self.producer.poll(0.1)
            self.producer.poll(0)

        undelivered = self.producer.flush(30)
        elapsed = max(time.perf_counter() - started, 0.000001)
        return {
            "queued": queued,
            "delivered": counters["delivered"],
            "errors": counters["errors"] + undelivered,
            "elapsed_seconds": round(elapsed, 4),
            "events_per_second": round(counters["delivered"] / elapsed, 2),
        }

