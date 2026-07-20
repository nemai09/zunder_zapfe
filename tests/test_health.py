import pytest
from fastapi.testclient import TestClient

from zunder_zapfe.hardware.layer import HardwareLayer
from zunder_zapfe.hardware.simulators import (
    SimulatedEmergencyStop,
    SimulatedFlowMeter,
    SimulatedNfcReader,
    SimulatedValve,
)
from zunder_zapfe.main import create_app


def simulated_hardware() -> HardwareLayer:
    return HardwareLayer(
        nfc=SimulatedNfcReader(),
        valve=SimulatedValve(),
        flow_meter=SimulatedFlowMeter(),
        emergency_stop=SimulatedEmergencyStop(),
    )


@pytest.fixture
def client() -> TestClient:
    with TestClient(create_app(simulated_hardware())) as test_client:
        yield test_client


def test_health_endpoint_reports_ready(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["application"] == "zunder-zapfe"
    assert response.json()["version"] == "0.3.0-alpha.1"
    assert response.json()["build"].startswith("zzapfe_v0.3.0_alpha.1_")
    assert response.json()["build"].endswith(response.json()["revision"])


def test_kiosk_page_is_available(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Zunder Zapfe" in response.text
    assert "NFC-Leser" in response.text
    assert 'href="/static/styles.css?v=0.3.0-alpha.1"' in response.text
    assert 'src="/static/app.js?v=0.3.0-alpha.1"' in response.text
    assert response.headers["cache-control"] == "no-store"
    script = client.get("/static/app.js?v=0.3.0-alpha.1")
    assert script.status_code == 200
    assert script.headers["cache-control"] == "no-store"
    assert '"use strict"' in script.text


def test_kiosk_options_preserve_portions_and_expose_manual_alpha_limits(
    client: TestClient,
) -> None:
    response = client.get("/api/tap/options")

    assert response.status_code == 200
    assert response.json() == {
        "standard_portions_ml": [300, 500],
        "special_portion_ml": None,
        "session_timeout_seconds": 15,
        "manual_press_debounce_ms": 120,
        "manual_maximum_pour_seconds": 30,
        "debug_flow_watchdog_disabled": True,
        "admin_session_timeout_seconds": 30,
    }


def test_nfc_status_uses_injected_hardware(client: TestClient) -> None:
    response = client.get("/api/nfc/status")

    assert response.status_code == 200
    assert response.json()["state"] == "ready"
    assert response.json()["simulated"] is True
    assert "uid" in response.json()


def test_hardware_status_identifies_simulated_components(client: TestClient) -> None:
    response = client.get("/api/hardware/status")

    assert response.status_code == 200
    assert set(response.json()) == {"nfc", "valve", "flow_meter", "emergency_stop"}
    assert all(component["simulated"] for component in response.json().values())
    assert response.json()["valve"]["is_open"] is False


def test_tap_starts_idle_with_closed_valve(client: TestClient) -> None:
    response = client.get("/api/tap/status")

    assert response.status_code == 200
    assert response.json()["state"] == "idle"
    assert response.json()["valve_open"] is False
