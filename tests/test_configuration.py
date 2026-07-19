import pytest

from zunder_zapfe.configuration import KioskSettings, load_kiosk_settings


def test_kiosk_defaults_use_approved_alpha_portions() -> None:
    settings = load_kiosk_settings({})

    assert settings.standard_portions_ml == (300, 500)
    assert settings.session_timeout_seconds == 60


def test_kiosk_settings_can_be_overridden_without_source_change() -> None:
    settings = load_kiosk_settings(
        {
            "ZUNDER_ZAPFE_STANDARD_PORTIONS_ML": "250, 400, 500",
            "ZUNDER_ZAPFE_SESSION_TIMEOUT_SECONDS": "90",
        }
    )

    assert settings == KioskSettings(
        standard_portions_ml=(250, 400, 500),
        session_timeout_seconds=90,
    )


@pytest.mark.parametrize(
    "environment",
    [
        {"ZUNDER_ZAPFE_STANDARD_PORTIONS_ML": "500"},
        {"ZUNDER_ZAPFE_STANDARD_PORTIONS_ML": "300,300"},
        {"ZUNDER_ZAPFE_STANDARD_PORTIONS_ML": "300,nope"},
        {"ZUNDER_ZAPFE_SESSION_TIMEOUT_SECONDS": "0"},
    ],
)
def test_invalid_kiosk_settings_are_rejected(environment: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        load_kiosk_settings(environment)
