from __future__ import annotations

import copy
import random
import uuid
from datetime import datetime, timezone
from typing import Any


DISTRICTS = [
    {"id": "D01", "name": "Distrito Centro", "weight": 30, "units": 24},
    {"id": "D02", "name": "Distrito Norte", "weight": 19, "units": 16},
    {"id": "D03", "name": "Distrito Sur", "weight": 16, "units": 13},
    {"id": "D04", "name": "Distrito Este", "weight": 15, "units": 12},
    {"id": "D05", "name": "Distrito Oeste", "weight": 12, "units": 10},
    {"id": "D06", "name": "Distrito Costero", "weight": 8, "units": 7},
]

EMERGENCY_TYPES = [
    ("Emergencia médica", 31),
    ("Accidente vehicular", 25),
    ("Seguridad ciudadana", 21),
    ("Incendio", 12),
    ("Desastre natural", 6),
    ("Rescate", 5),
]

SCENARIOS = {
    "Operación normal": {
        "types": EMERGENCY_TYPES,
        "district_weights": [30, 19, 16, 15, 12, 8],
    },
    "Accidente múltiple": {
        "types": [("Accidente vehicular", 68), ("Emergencia médica", 24), ("Rescate", 8)],
        "district_weights": [15, 10, 8, 45, 14, 8],
    },
    "Tormenta severa": {
        "types": [("Desastre natural", 48), ("Rescate", 24), ("Emergencia médica", 18), ("Accidente vehicular", 10)],
        "district_weights": [12, 14, 16, 14, 14, 30],
    },
    "Evento masivo": {
        "types": [("Seguridad ciudadana", 42), ("Emergencia médica", 35), ("Rescate", 13), ("Accidente vehicular", 10)],
        "district_weights": [58, 11, 8, 9, 8, 6],
    },
}

LOCATIONS = [
    "Avenida principal, sector 1",
    "Boulevard del distrito",
    "Mercado municipal",
    "Terminal de transporte",
    "Zona residencial",
    "Carretera de acceso",
    "Centro educativo",
    "Zona comercial",
]

DESCRIPTIONS = {
    "Emergencia médica": "Persona requiere asistencia médica inmediata",
    "Accidente vehicular": "Colisión vehicular reportada por ciudadanos",
    "Seguridad ciudadana": "Incidente de seguridad en progreso",
    "Incendio": "Presencia de humo y fuego reportada",
    "Desastre natural": "Afectación relacionada con condiciones climáticas",
    "Rescate": "Persona en situación de riesgo requiere rescate",
}


def _priority_for(emergency_type: str) -> int:
    if emergency_type in {"Incendio", "Desastre natural", "Rescate"}:
        return random.choices([1, 2, 3, 4, 5], weights=[2, 5, 15, 36, 42], k=1)[0]
    if emergency_type == "Emergencia médica":
        return random.choices([1, 2, 3, 4, 5], weights=[4, 10, 30, 38, 18], k=1)[0]
    return random.choices([1, 2, 3, 4, 5], weights=[8, 20, 38, 25, 9], k=1)[0]


def create_event(
    district_id: str | None = None,
    emergency_type: str | None = None,
    priority: int | None = None,
    location: str | None = None,
    description: str | None = None,
    scenario: str = "Operación normal",
) -> dict[str, Any]:
    district = next((item for item in DISTRICTS if item["id"] == district_id), None)
    scenario_config = SCENARIOS.get(scenario, SCENARIOS["Operación normal"])
    district = district or random.choices(DISTRICTS, weights=scenario_config["district_weights"], k=1)[0]

    if not emergency_type:
        labels, weights = zip(*scenario_config["types"])
        emergency_type = random.choices(labels, weights=weights, k=1)[0]

    report_number = f"EM-{uuid.uuid4().hex[:8].upper()}"
    return {
        "schema_version": 1,
        "report_number": report_number,
        "district_id": district["id"],
        "district_name": district["name"],
        "emergency_type": emergency_type,
        "priority": priority or _priority_for(emergency_type),
        "location": location or random.choice(LOCATIONS),
        "description": description or DESCRIPTIONS.get(emergency_type, "Emergencia reportada"),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "status": "Recibida",
        "assigned_unit": None,
        "operator": "Alejandro",
        "source": "central-911-generator",
        "scenario": scenario,
    }


def create_batch(
    count: int,
    imperfection_rate: float = 0.02,
    scenario: str = "Operación normal",
) -> list[dict[str, Any]]:
    if count < 1:
        raise ValueError("El lote debe contener al menos un evento")
    if not 0 <= imperfection_rate <= 0.25:
        raise ValueError("La tasa de imperfecciones debe estar entre 0 y 0.25")

    events: list[dict[str, Any]] = []
    for _ in range(count):
        roll = random.random()
        if events and roll < imperfection_rate / 2:
            duplicate = copy.deepcopy(random.choice(events))
            duplicate["simulated_issue"] = "duplicate"
            events.append(duplicate)
            continue

        event = create_event(scenario=scenario)
        if roll < imperfection_rate:
            event.pop(random.choice(["district_id", "emergency_type", "occurred_at"]))
            event["simulated_issue"] = "malformed"
        events.append(event)
    return events
