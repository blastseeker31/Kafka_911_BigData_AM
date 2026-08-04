from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    kafka_bootstrap_servers: str = os.getenv(
        "KAFKA_BOOTSTRAP_SERVERS",
        "localhost:9092",
    )
    kafka_topic: str = os.getenv("KAFKA_TOPIC", "emergency-calls")
    kafka_group_id: str = os.getenv("KAFKA_GROUP_ID", "911-processing-v1")
    mongo_uri: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    mongo_database: str = os.getenv("MONGO_DATABASE", "central_911")
    app_user: str = os.getenv("APP_USER", "Alejandro")
    app_password: str = os.getenv("APP_PASSWORD", "911")


settings = Settings()

