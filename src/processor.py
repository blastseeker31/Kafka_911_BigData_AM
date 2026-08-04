from __future__ import annotations

from datetime import datetime
from typing import Any


REQUIRED_FIELDS = {
    "report_number",
    "district_id",
    "district_name",
    "emergency_type",
    "priority",
    "location",
    "occurred_at",
    "status",
}


def validate_event(event: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - event.keys())
    if missing:
        errors.append(f"Campos faltantes: {', '.join(missing)}")

    priority = event.get("priority")
    if not isinstance(priority, int) or isinstance(priority, bool) or not 1 <= priority <= 5:
        errors.append("La prioridad debe ser un entero entre 1 y 5")

    occurred_at = event.get("occurred_at")
    if occurred_at:
        try:
            datetime.fromisoformat(str(occurred_at).replace("Z", "+00:00"))
        except ValueError:
            errors.append("occurred_at no contiene una fecha ISO-8601 válida")
    return errors


def load_state(active_calls: int, available_units: int) -> dict[str, float | str | int]:
    ratio = active_calls / available_units if available_units else float("inf")
    if ratio > 1:
        exposure = "Crítica"
    elif ratio >= 0.6:
        exposure = "Atención"
    else:
        exposure = "Estable"
    return {
        "active_calls": active_calls,
        "available_units": available_units,
        "balance": available_units - active_calls,
        "load_ratio": round(ratio, 2),
        "exposure": exposure,
    }

