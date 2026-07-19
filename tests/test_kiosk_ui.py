from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = PROJECT_ROOT / "src" / "zunder_zapfe" / "web"


def test_zz_ui_001_kiosk_assets_are_offline_and_packaged_locally() -> None:
    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")

    assert 'href="/static/styles.css"' in html
    assert 'src="/static/app.js"' in html
    assert "https://" not in html
    assert "http://" not in html


def test_zz_nfr_003_kiosk_exposes_complete_touch_flow() -> None:
    script = (WEB_ROOT / "app.js").read_text(encoding="utf-8")

    for route in (
        "/api/tap/options",
        "/api/tap/portion",
        "/api/tap/portion/abort",
        "/api/tap/top-up/start",
        "/api/tap/top-up/stop",
        "/api/tap/heartbeat",
        "/api/session/logout",
        "/api/tap/safety/reset",
    ):
        assert route in script

    for release_event in ("pointerup", "pointercancel", "lostpointercapture"):
        assert release_event in script
    assert 'window.addEventListener("blur", stopTopUp)' in script
    assert "if (document.hidden) stopTopUp()" in script


def test_kiosk_does_not_render_nfc_uid() -> None:
    script = (WEB_ROOT / "app.js").read_text(encoding="utf-8")

    assert "nfc.uid" not in script
