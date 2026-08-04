from __future__ import annotations

import copy
import random
import uuid
from datetime import datetime, timezone
from typing import Any


CITIES = [
    {"id": "TGU", "name": "Tegucigalpa", "weight": 46, "units": {"Ambulancia": 18, "Patrulla": 22, "Bomberos": 8, "Rescate": 6}},
    {"id": "SPS", "name": "San Pedro Sula", "weight": 38, "units": {"Ambulancia": 14, "Patrulla": 18, "Bomberos": 7, "Rescate": 5}},
    {"id": "LCE", "name": "La Ceiba", "weight": 16, "units": {"Ambulancia": 7, "Patrulla": 8, "Bomberos": 4, "Rescate": 4}},
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
    "Operación normal": {"types": EMERGENCY_TYPES, "city_weights": [46, 38, 16]},
    "Accidente múltiple": {"types": [("Accidente vehicular", 68), ("Emergencia médica", 24), ("Rescate", 8)], "city_weights": [42, 45, 13]},
    "Tormenta severa": {"types": [("Desastre natural", 48), ("Rescate", 24), ("Emergencia médica", 18), ("Accidente vehicular", 10)], "city_weights": [35, 25, 40]},
    "Evento masivo": {"types": [("Seguridad ciudadana", 42), ("Emergencia médica", 35), ("Rescate", 13), ("Accidente vehicular", 10)], "city_weights": [55, 35, 10]},
}

NEIGHBORHOODS = {
    "Tegucigalpa": ["Comayagüela", "Kennedy", "Miraflores", "El Centro", "Lomas del Guijarro", "Anillo Periférico"],
    "San Pedro Sula": ["Barrio Guamilito", "Río de Piedras", "Colonia Trejo", "El Centro", "Satélite", "Circunvalación"],
    "La Ceiba": ["El Centro", "Barrio La Isla", "Solares Nuevos", "Satuye", "La Merced", "Carretera a Tela"],
}

DESCRIPTIONS = {
    "Emergencia médica": "Persona requiere asistencia médica inmediata",
    "Accidente vehicular": "Colisión vehicular reportada por ciudadanos",
    "Seguridad ciudadana": "Incidente de seguridad en progreso",
    "Incendio": "Presencia de humo y fuego reportada",
    "Desastre natural": "Afectación relacionada con condiciones climáticas",
    "Rescate": "Persona en situación de riesgo requiere rescate",
}


def _priority_for(emergency_type: str) -> int:
    weights = [2, 5, 15, 36, 42] if emergency_type in {"Incendio", "Desastre natural", "Rescate"} else [4, 10, 30, 38, 18] if emergency_type == "Emergencia médica" else [8, 20, 38, 25, 9]
    return random.choices([1, 2, 3, 4, 5], weights=weights, k=1)[0]


def create_event(city_id: str | None = None, emergency_type: str | None = None, priority: int | None = None, location: str | None = None, description: str | None = None, people_at_risk: int | None = None, neighborhood: str | None = None, scenario: str = "Operación normal", **legacy: Any) -> dict[str, Any]:
    city_id = city_id or legacy.get("district_id")
    city = next((item for item in CITIES if item["id"] == city_id), None)
    config = SCENARIOS.get(scenario, SCENARIOS["Operación normal"])
    city = city or random.choices(CITIES, weights=config["city_weights"], k=1)[0]
    if not emergency_type:
        labels, weights = zip(*config["types"])
        emergency_type = random.choices(labels, weights=weights, k=1)[0]
    name = city["name"]
    return {
        "schema_version": 2,
        "report_number": f"EM-{uuid.uuid4().hex[:8].upper()}",
        "city_id": city["id"], "city_name": name,
        "neighborhood": neighborhood or random.choice(NEIGHBORHOODS[name]),
        "emergency_type": emergency_type,
        "priority": priority or _priority_for(emergency_type),
        "location": location or "Punto de referencia no especificado",
        "description": description or DESCRIPTIONS.get(emergency_type, "Emergencia reportada"),
        "people_at_risk": max(1, people_at_risk or random.randint(1, 5)),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "status": "Nuevo", "assigned_units": [], "operator": "Alejandro",
        "source": "central-911-generator", "scenario": scenario,
    }


def create_batch(count: int, imperfection_rate: float = 0.02, scenario: str = "Operación normal") -> list[dict[str, Any]]:
    if count < 1: raise ValueError("El lote debe contener al menos un evento")
    if not 0 <= imperfection_rate <= 0.25: raise ValueError("La tasa de imperfecciones debe estar entre 0 y 0.25")
    events: list[dict[str, Any]] = []
    for _ in range(count):
        roll = random.random()
        if events and roll < imperfection_rate / 2:
            duplicate = copy.deepcopy(random.choice(events)); duplicate["simulated_issue"] = "duplicate"; events.append(duplicate); continue
        event = create_event(scenario=scenario)
        if roll < imperfection_rate:
            event.pop(random.choice(["city_id", "emergency_type", "occurred_at"])); event["simulated_issue"] = "malformed"
        events.append(event)
    return events


# Compatibilidad para consumidores externos antiguos: no son distritos, son ciudades.
DISTRICTS = CITIES
