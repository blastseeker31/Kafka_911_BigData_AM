from __future__ import annotations

from datetime import datetime
from typing import Any

from src.event_factory import CITIES

REQUIRED_FIELDS = {"report_number", "city_id", "city_name", "neighborhood", "emergency_type", "priority", "location", "description", "people_at_risk", "occurred_at", "status"}
STATUSES = ["Nuevo", "Despachado", "En atención", "Cerrado"]


def validate_event(event: dict[str, Any]) -> list[str]:
    errors = []
    missing = sorted(REQUIRED_FIELDS - event.keys())
    if missing: errors.append(f"Campos faltantes: {', '.join(missing)}")
    if event.get("city_id") not in {city["id"] for city in CITIES}: errors.append("La ciudad debe ser Tegucigalpa, San Pedro Sula o La Ceiba")
    if not isinstance(event.get("priority"), int) or isinstance(event.get("priority"), bool) or not 1 <= event.get("priority", 0) <= 5: errors.append("La prioridad debe ser un entero entre 1 y 5")
    if not isinstance(event.get("people_at_risk"), int) or event.get("people_at_risk", 0) < 1: errors.append("Personas en riesgo debe ser un entero positivo")
    try: datetime.fromisoformat(str(event.get("occurred_at", "")).replace("Z", "+00:00"))
    except ValueError: errors.append("occurred_at no contiene una fecha ISO-8601 válida")
    return errors


def load_state(active_calls: int, available_units: int) -> dict[str, float | str | int]:
    ratio = active_calls / available_units if available_units else float("inf")
    exposure = "Crítica" if ratio > 1 else "Atención" if ratio >= 0.6 else "Estable"
    return {"active_calls": active_calls, "available_units": available_units, "balance": available_units - active_calls, "load_ratio": round(ratio, 2), "exposure": exposure}
