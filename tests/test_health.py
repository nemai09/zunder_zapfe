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
