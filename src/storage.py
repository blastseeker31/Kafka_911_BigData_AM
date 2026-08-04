from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.errors import DuplicateKeyError

from src.config import settings
from src.event_factory import DISTRICTS
from src.processor import load_state


class EmergencyStorage:
    def __init__(self) -> None:
        self.client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=3000)
        self.db = self.client[settings.mongo_database]
        self.emergencies = self.db.emergencies
        self.metrics = self.db.district_metrics
        self.dead_letters = self.db.dead_letters
        self._prepare()

    def _prepare(self) -> None:
        self.emergencies.create_index("report_number", unique=True)
        self.emergencies.create_index([("district_id", ASCENDING), ("occurred_at", DESCENDING)])
        self.dead_letters.create_index("received_at")
        for district in DISTRICTS:
            self.metrics.update_one(
                {"district_id": district["id"]},
                {
                    "$setOnInsert": {
                        "district_name": district["name"],
                        "active_calls": 0,
                        "critical_calls": 0,
                        "processed_calls": 0,
                        "available_units": district["units"],
                        "type_counts": {},
                    }
                },
                upsert=True,
            )

    def ping(self) -> bool:
        return bool(self.client.admin.command("ping").get("ok"))

    def save_valid_event(self, event: dict[str, Any]) -> bool:
        document = dict(event)
        document["processed_at"] = datetime.now(timezone.utc)
        try:
            self.emergencies.insert_one(document)
        except DuplicateKeyError:
            return False

        increments: dict[str, int] = {
            "active_calls": 1,
            "processed_calls": 1,
            f"type_counts.{event['emergency_type']}": 1,
        }
        if int(event["priority"]) >= 4:
            increments["critical_calls"] = 1

        self.metrics.update_one(
            {"district_id": event["district_id"]},
            {
                "$inc": increments,
                "$set": {
                    "district_name": event["district_name"],
                    "updated_at": datetime.now(timezone.utc),
                },
            },
            upsert=True,
        )
        return True

    def save_dead_letter(self, event: dict[str, Any], errors: list[str]) -> None:
        self.dead_letters.insert_one(
            {
                "event": event,
                "errors": errors,
                "received_at": datetime.now(timezone.utc),
            }
        )

    def dashboard_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for metric in self.metrics.find().sort("district_id", ASCENDING):
            state = load_state(metric.get("active_calls", 0), metric.get("available_units", 0))
            rows.append(
                {
                    "Distrito": metric.get("district_name", metric["district_id"]),
                    "Activas": state["active_calls"],
                    "Críticas": metric.get("critical_calls", 0),
                    "Unidades": state["available_units"],
                    "Balance": state["balance"],
                    "Carga": state["load_ratio"],
                    "Exposición": state["exposure"],
                }
            )
        return rows

    def summary(self) -> dict[str, int]:
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "active": {"$sum": "$active_calls"},
                    "critical": {"$sum": "$critical_calls"},
                    "units": {"$sum": "$available_units"},
                    "processed": {"$sum": "$processed_calls"},
                }
            }
        ]
        result = next(self.metrics.aggregate(pipeline), {})
        return {key: int(result.get(key, 0)) for key in ("active", "critical", "units", "processed")}

    def recent_events(self, limit: int = 30, district_name: str | None = None) -> list[dict[str, Any]]:
        query = {"district_name": district_name} if district_name else {}
        return list(self.emergencies.find(query, {"_id": 0}).sort("processed_at", DESCENDING).limit(limit))

    def get_event(self, report_number: str) -> dict[str, Any] | None:
        return self.emergencies.find_one({"report_number": report_number}, {"_id": 0})

    def update_event(self, report_number: str, status: str, assigned_unit: str, observation: str) -> bool:
        current = self.emergencies.find_one({"report_number": report_number})
        if not current:
            return False

        was_active = current.get("status") != "Resuelta"
        will_be_active = status != "Resuelta"
        result = self.emergencies.update_one(
            {"report_number": report_number},
            {
                "$set": {
                    "status": status,
                    "assigned_unit": assigned_unit or None,
                    "observation": observation,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        if result.modified_count and was_active != will_be_active:
            direction = 1 if will_be_active else -1
            increments = {"active_calls": direction}
            if int(current.get("priority", 0)) >= 4:
                increments["critical_calls"] = direction
            self.metrics.update_one({"district_id": current["district_id"]}, {"$inc": increments})
        return bool(result.matched_count)

    def dead_letter_count(self) -> int:
        return self.dead_letters.count_documents({})

    def reset_demo_data(self) -> None:
        self.emergencies.delete_many({})
        self.dead_letters.delete_many({})
        self.metrics.delete_many({})
        self._prepare()
