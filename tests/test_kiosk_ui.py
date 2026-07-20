from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = PROJECT_ROOT / "src" / "zunder_zapfe" / "web"


def test_zz_ui_001_kiosk_assets_are_offline_and_packaged_locally() -> None:
    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")

    assert 'href="/static/styles.css?v=0.2.0-alpha.3"' in html
    assert 'src="/static/app.js?v=0.2.0-alpha.3"' in html
    assert "https://" not in html
    assert "http://" not in html


def test_zz_ui_004_and_nfr_005_kiosk_exposes_manual_touch_flow() -> None:
    script = (WEB_ROOT / "app.js").read_text(encoding="utf-8")

    for route in (
        "/api/tap/options",
        "/api/tap/manual/start",
        "/api/tap/manual/stop",
        "/api/tap/heartbeat",
        "/api/session/logout",
        "/api/tap/safety/reset",
    ):
        assert route in script

    for release_event in ("pointerup", "pointercancel", "lostpointercapture"):
        assert release_event in script
    assert 'window.addEventListener("blur", releaseManual)' in script
    assert "if (document.hidden) releaseManual()" in script
    assert "manual_press_debounce_ms ?? 120" in script

    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    assert 'id="manual-button"' in html
    assert 'id="valve-status"' in html
    assert "valve_open" in script
    assert "DEBUG · Ventil" in script
    assert 'id="portion-grid"' not in html
    assert 'id="top-up-button"' not in html


def test_kiosk_does_not_render_nfc_uid() -> None:
    script = (WEB_ROOT / "app.js").read_text(encoding="utf-8")

    assert "nfc.uid" not in script
