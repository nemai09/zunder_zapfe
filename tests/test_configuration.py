import pytest

from zunder_zapfe.configuration import KioskSettings, load_kiosk_settings


def test_kiosk_defaults_use_approved_alpha_portions() -> None:
    settings = load_kiosk_settings({})

    assert settings.standard_portions_ml == (300, 500)
    assert settings.session_timeout_seconds == 15
    assert settings.manual_press_debounce_ms == 120
    assert settings.manual_maximum_pour_seconds == 30
    assert settings.debug_disable_flow_watchdog is True


def test_kiosk_settings_can_be_overridden_without_source_change() -> None:
    settings = load_kiosk_settings(
        {
            "ZUNDER_ZAPFE_STANDARD_PORTIONS_ML": "250, 400, 500",
            "ZUNDER_ZAPFE_SESSION_TIMEOUT_SECONDS": "90",
            "ZUNDER_ZAPFE_MANUAL_PRESS_DEBOUNCE_MS": "150",
            "ZUNDER_ZAPFE_MANUAL_MAXIMUM_POUR_SECONDS": "45",
            "ZUNDER_ZAPFE_DEBUG_DISABLE_FLOW_WATCHDOG": "0",
        }
    )

    assert settings == KioskSettings(
        standard_portions_ml=(250, 400, 500),
        session_timeout_seconds=90,
        manual_press_debounce_ms=150,
        manual_maximum_pour_seconds=45,
        debug_disable_flow_watchdog=False,
    )


@pytest.mark.parametrize(
    "environment",
    [
        {"ZUNDER_ZAPFE_STANDARD_PORTIONS_ML": "500"},
        {"ZUNDER_ZAPFE_STANDARD_PORTIONS_ML": "300,300"},
        {"ZUNDER_ZAPFE_STANDARD_PORTIONS_ML": "300,nope"},
        {"ZUNDER_ZAPFE_SESSION_TIMEOUT_SECONDS": "0"},
        {"ZUNDER_ZAPFE_MANUAL_PRESS_DEBOUNCE_MS": "-1"},
        {"ZUNDER_ZAPFE_MANUAL_MAXIMUM_POUR_SECONDS": "0"},
        {"ZUNDER_ZAPFE_DEBUG_DISABLE_FLOW_WATCHDOG": "true"},
    ],
)
def test_invalid_kiosk_settings_are_rejected(environment: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        load_kiosk_settings(environment)
