from services.alert_service import should_trigger


def test_alert_condition_logic():
    assert should_trigger("above", 101, 100)
    assert not should_trigger("above", 99, 100)
    assert should_trigger("below", 99, 100)
    assert not should_trigger("below", 101, 100)
