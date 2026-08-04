from src.event_factory import create_event
from src.processor import load_state, validate_event


def test_valid_event_passes_validation():
    assert validate_event(create_event()) == []


def test_missing_and_invalid_values_are_rejected():
    event = create_event()
    event.pop("district_id")
    event["priority"] = 9
    errors = validate_event(event)
    assert len(errors) == 2


def test_load_state_exposure_levels():
    assert load_state(4, 10)["exposure"] == "Estable"
    assert load_state(8, 10)["exposure"] == "Atención"
    assert load_state(11, 10)["exposure"] == "Crítica"
    assert load_state(11, 10)["balance"] == -1

