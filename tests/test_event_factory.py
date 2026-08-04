from src.event_factory import DISTRICTS, create_batch, create_event


def test_create_event_has_required_fields():
    event = create_event(district_id="D01", emergency_type="Incendio", priority=5)
    assert event["district_id"] == "D01"
    assert event["priority"] == 5
    assert event["report_number"].startswith("EM-")
    assert {"location", "occurred_at", "status"}.issubset(event)


def test_batch_size_and_distribution_domain():
    events = create_batch(250, imperfection_rate=0)
    assert len(events) == 250
    assert {event["district_id"] for event in events}.issubset({item["id"] for item in DISTRICTS})


def test_batch_can_include_controlled_imperfections():
    events = create_batch(500, imperfection_rate=0.10)
    assert any("simulated_issue" in event for event in events)


def test_accident_scenario_changes_event_distribution():
    events = create_batch(500, imperfection_rate=0, scenario="Accidente múltiple")
    accidents = sum(event["emergency_type"] == "Accidente vehicular" for event in events)
    assert accidents > 250
