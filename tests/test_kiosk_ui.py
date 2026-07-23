from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = PROJECT_ROOT / "src" / "zunder_zapfe" / "web"


def test_zz_ui_001_kiosk_assets_are_offline_and_packaged_locally() -> None:
    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")

    assert 'href="/static/styles.css?v=0.4.0-alpha.1"' in html
    assert 'src="/static/app.js?v=0.4.0-alpha.1"' in html
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
        "/api/session/activity",
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
    assert 'class="tap-button"' in html
    assert 'class="dashboard-row"' in html
    assert 'class="info-panel dashboard-info"' in html
    assert 'class="stat-row"' in html
    assert 'class="button button-logout"' in html
    assert 'id="session-timeout-fill"' in html
    assert "session_remaining_ms" in script
    assert "session_timeout_seconds" in script
    assert "WIFI_REFRESH_MS = 30000" in script
    assert "NFC_REFRESH_MS = 2000" in script
    assert "CONTEXT_REFRESH_MS = 15000" in script
    assert "HEALTH_REFRESH_MS = 30000" in script
    assert "renderIfChanged()" in script
    assert "window.setTimeout(refreshLoop, STATUS_REFRESH_MS)" in script
    assert "window.setInterval(refresh" not in script
    assert 'id="valve-status"' in html
    assert 'id="wifi-status"' in html
    assert "valve_open" in script
    assert "DEBUG · Ventil" in script
    assert 'id="portion-grid"' not in html
    assert 'id="top-up-button"' not in html
    assert "border: 1px solid var(--line)" not in styles_for_rule(
        (WEB_ROOT / "styles.css").read_text(encoding="utf-8"),
        ".wifi-status",
    )
    assert "transform: scaleX(1)" in styles_for_rule(
        (WEB_ROOT / "styles.css").read_text(encoding="utf-8"),
        ".session-timeout-fill",
    )
    assert "transition: width" not in styles_for_rule(
        (WEB_ROOT / "styles.css").read_text(encoding="utf-8"),
        ".session-timeout-fill",
    )


def test_kiosk_does_not_render_nfc_uid() -> None:
    script = (WEB_ROOT / "app.js").read_text(encoding="utf-8")

    assert "nfc.uid" not in script


def styles_for_rule(styles: str, selector: str) -> str:
    return styles.split(f"{selector} {{", maxsplit=1)[1].split("}", maxsplit=1)[0]


def test_zz_ui_006_admin_mode_and_live_wristband_flow_are_packaged() -> None:
    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    script = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    system_html = (WEB_ROOT / "system.html").read_text(encoding="utf-8")
    system_script = (WEB_ROOT / "system.js").read_text(encoding="utf-8")

    assert 'id="admin-button"' in html
    assert 'class="session-actions"' in html
    assert 'data-screen="admin"' in html
    assert 'data-admin-panel="users"' in html
    assert 'id="capture-card-button"' in html
    assert 'id="user-search"' in html
    assert 'id="user-filter"' in html
    assert "Karte nicht erkannt" in script
    assert "Karte gesperrt" in script
    assert "Zuordnung entfernen" in script
    assert 'window.location.assign("/system")' in script
    assert 'api("/api/admin/session/enter"' in script
    assert "ZUNDER_ZAPFE" in system_html
    assert "/api/admin/wifi/mode" in system_script
    assert '"nfc_capture"' in script
    assert "Armband wird zugeordnet." in script
    assert 'data-screen="registration"' in html
    assert "registration_welcome" in script
    for route in (
        "/api/admin/session/exit",
        "/api/admin/users",
        "/nfc-cards/capture",
        "/api/admin/nfc-cards/",
        "/api/admin/settings",
    ):
        assert route in script
