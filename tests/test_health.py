from fastapi.testclient import TestClient

from zunder_zapfe.main import app


def test_health_endpoint_reports_ready() -> None:
    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["application"] == "zunder-zapfe"


def test_kiosk_page_is_available() -> None:
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "Zunder Zapfe" in response.text
    assert "NFC-Leser" in response.text


def test_nfc_status_is_available_without_reader() -> None:
    response = TestClient(app).get("/api/nfc/status")

    assert response.status_code == 200
    assert response.json()["state"] in {
        "starting",
        "unavailable",
        "disconnected",
        "ready",
        "card",
        "error",
    }
    assert "uid" in response.json()
