from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.errors import DuplicateKeyError

from src.config import settings
from src.event_factory import CITIES
from src.processor import STATUSES, load_state


class EmergencyStorage:
    def __init__(self) -> None:
        self.client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=3000)
        self.db = self.client[settings.mongo_database]
        self.emergencies = self.db.emergencies; self.metrics = self.db.city_metrics; self.dead_letters = self.db.dead_letters
        self._prepare()

    def _prepare(self) -> None:
        self.emergencies.create_index("report_number", unique=True)
        self.emergencies.create_index([("status", ASCENDING), ("priority", DESCENDING), ("occurred_at", DESCENDING)])
        self.emergencies.create_index([("city_id", ASCENDING), ("emergency_type", ASCENDING)])
        self.dead_letters.create_index("received_at")
        for city in CITIES:
            total = sum(city["units"].values())
            self.metrics.update_one({"city_id": city["id"]}, {"$setOnInsert": {"city_name": city["name"], "active_calls": 0, "critical_calls": 0, "processed_calls": 0, "available_units": total, "unit_totals": city["units"]}}, upsert=True)

    def ping(self) -> bool: return bool(self.client.admin.command("ping").get("ok"))

    def save_valid_event(self, event: dict[str, Any]) -> bool:
        document = dict(event); document["processed_at"] = datetime.now(timezone.utc)
        try: self.emergencies.insert_one(document)
        except DuplicateKeyError: return False
        inc = {"active_calls": 1, "processed_calls": 1}
        if int(event["priority"]) >= 4: inc["critical_calls"] = 1
        self.metrics.update_one({"city_id": event["city_id"]}, {"$inc": inc, "$set": {"updated_at": datetime.now(timezone.utc)}}, upsert=True)
        return True

    def save_dead_letter(self, event: dict[str, Any], errors: list[str]) -> None: self.dead_letters.insert_one({"event": event, "errors": errors, "received_at": datetime.now(timezone.utc)})

    def summary(self) -> dict[str, int]:
        result = next(self.metrics.aggregate([{"$group": {"_id": None, "new": {"$sum": {"$cond": [{"$eq": ["$active_calls", "$active_calls"]}, 0, 0]}}, "critical": {"$sum": "$critical_calls"}, "units": {"$sum": "$available_units"}, "processed": {"$sum": "$processed_calls"}}}]), {})
        # La cola nueva se calcula directamente para que los cambios de estado sean siempre consistentes.
        return {"new": self.emergencies.count_documents({"status": "Nuevo"}), "active": self.emergencies.count_documents({"status": {"$ne": "Cerrado"}}), "critical": self.emergencies.count_documents({"priority": {"$gte": 4}, "status": {"$ne": "Cerrado"}}), "units": int(result.get("units", 0)), "occupied": self.emergencies.count_documents({"status": {"$in": ["Despachado", "En atención"]}}), "processed": int(result.get("processed", 0))}

    def city_rows(self) -> list[dict[str, Any]]:
        rows = []
        for metric in self.metrics.find().sort("city_id", ASCENDING):
            state = load_state(metric.get("active_calls", 0), metric.get("available_units", 0))
            rows.append({"Ciudad": metric.get("city_name"), "Nuevos": self.emergencies.count_documents({"city_id": metric["city_id"], "status": "Nuevo"}), "Activos": state["active_calls"], "Disponibles": state["available_units"], "Ocupadas": metric.get("unit_totals", {}) and sum(metric.get("unit_totals", {}).values()) - state["available_units"], "Presión": state["exposure"], "Carga": state["load_ratio"]})
        return rows

    def query_events(self, page: int = 1, page_size: int = 25, search: str = "", city: str = "Todas", event_type: str = "Todos", priority: str = "Todas", status: str = "Todos", sort: str = "Más recientes") -> tuple[list[dict[str, Any]], int]:
        query: dict[str, Any] = {}
        if search.strip(): query["$or"] = [{"report_number": {"$regex": search.strip(), "$options": "i"}}, {"description": {"$regex": search.strip(), "$options": "i"}}, {"location": {"$regex": search.strip(), "$options": "i"}}]
        if city != "Todas": query["city_name"] = city
        if event_type != "Todos": query["emergency_type"] = event_type
        if priority != "Todas": query["priority"] = int(priority)
        if status != "Todos": query["status"] = status
        sort_field, direction = (("priority", DESCENDING) if sort == "Prioridad" else ("occurred_at", DESCENDING))
        total = self.emergencies.count_documents(query); skip = max(page - 1, 0) * page_size
        return list(self.emergencies.find(query, {"_id": 0}).sort(sort_field, direction).skip(skip).limit(page_size)), total

    def get_event(self, report_number: str) -> dict[str, Any] | None: return self.emergencies.find_one({"report_number": report_number}, {"_id": 0})

    def update_event(self, report_number: str, status: str, assigned_units: list[str], observation: str) -> bool:
        if status not in STATUSES: return False
        current = self.get_event(report_number)
        if not current: return False
        was_active, will_be_active = current.get("status") != "Cerrado", status != "Cerrado"
        result = self.emergencies.update_one({"report_number": report_number}, {"$set": {"status": status, "assigned_units": assigned_units, "observation": observation, "updated_at": datetime.now(timezone.utc)}})
        if result.modified_count and was_active != will_be_active:
            inc = {"active_calls": 1 if will_be_active else -1}
            if int(current.get("priority", 0)) >= 4: inc["critical_calls"] = 1 if will_be_active else -1
            self.metrics.update_one({"city_id": current["city_id"]}, {"$inc": inc})
        return bool(result.matched_count)

    def dead_letter_count(self) -> int: return self.dead_letters.count_documents({})
    def reset_demo_data(self) -> None:
        self.emergencies.delete_many({}); self.dead_letters.delete_many({}); self.metrics.delete_many({}); self._prepare()
