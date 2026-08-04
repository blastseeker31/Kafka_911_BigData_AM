from src.event_factory import CITIES, create_batch, create_event


def test_create_event_has_operational_fields():
    event = create_event(city_id="TGU", emergency_type="Incendio", priority=5, people_at_risk=4)
    assert event["city_id"] == "TGU"
    assert event["city_name"] == "Tegucigalpa"
    assert event["priority"] == 5
    assert event["people_at_risk"] == 4
    assert {"neighborhood", "location", "description", "occurred_at", "status"}.issubset(event)


def test_batch_uses_only_honduran_cities():
    events = create_batch(250, imperfection_rate=0)
    assert {event["city_id"] for event in events}.issubset({item["id"] for item in CITIES})


def test_batch_can_include_controlled_imperfections():
    events = create_batch(500, imperfection_rate=0.10)
    assert any("simulated_issue" in event for event in events)


def test_accident_scenario_changes_event_distribution():
    events = create_batch(500, imperfection_rate=0, scenario="Accidente múltiple")
    accidents = sum(event["emergency_type"] == "Accidente vehicular" for event in events)
    assert accidents > 250
