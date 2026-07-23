from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = PROJECT_ROOT / "src" / "zunder_zapfe" / "web"


def test_zz_ui_008_smartphone_admin_assets_are_offline_and_responsive() -> None:
    html = (WEB_ROOT / "admin.html").read_text(encoding="utf-8")
    styles = (WEB_ROOT / "admin-styles.css").read_text(encoding="utf-8")

    assert 'name="viewport"' in html
    assert 'lang="de"' in html
    assert "https://" not in html
    assert "http://" not in html
    assert "@media (min-width: 700px)" in styles
    assert "env(safe-area-inset-bottom)" in styles
    assert 'id="login-form"' in html
    assert 'data-view="users"' in html
    assert 'data-view="kegs"' in html
    assert 'data-view="settings"' in html
    assert 'id="capture-dialog"' in html
    assert 'id="own-password-form"' in html
    assert 'id="keg-detach-button"' in html
    assert "optional" in html


def test_smartphone_admin_uses_only_the_protected_web_api() -> None:
    script = (WEB_ROOT / "admin-app.js").read_text(encoding="utf-8")

    for route in (
        "/api/web-auth/admins",
        "/api/web-auth/login",
        "/api/web-auth/session",
        "/api/web-auth/logout",
        "/api/web-auth/password",
        "/api/web-admin/users",
        "/nfc-cards/capture",
        "/api/web-admin/nfc-capture",
        "/api/web-admin/nfc-cards/",
        "/api/web-admin/booking-sessions",
        "/api/web-admin/kegs/detach",
    ):
        assert route in script
    assert "X-CSRF-Token" in script
    assert "zz_admin_csrf" in script
    assert "/api/admin/" not in script
    assert "/api/tap/" not in script
    assert "/api/simulator/" not in script
    assert "localStorage" not in script
    assert "sessionStorage" not in script


def test_reporting_wraps_audit_text_and_groups_login_bookings() -> None:
    html = (WEB_ROOT / "admin.html").read_text(encoding="utf-8")
    script = (WEB_ROOT / "admin-app.js").read_text(encoding="utf-8")
    styles = (WEB_ROOT / "admin-styles.css").read_text(encoding="utf-8")

    assert "eines NFC-Logins zusammengefasst" in html
    assert "/api/web-admin/booking-sessions" in script
    assert "booking.pour_count" in script
    assert "white-space: pre-wrap" in styles
    assert "overflow-wrap: anywhere" in styles


def test_smartphone_user_list_supports_event_sized_collections() -> None:
    html = (WEB_ROOT / "admin.html").read_text(encoding="utf-8")
    script = (WEB_ROOT / "admin-app.js").read_text(encoding="utf-8")

    assert 'id="user-search"' in html
    assert 'id="user-filter"' in html
    assert "filteredUsers()" in script
    assert "user.active_nfc_card_count" in script
    assert "Sperren" in script
    assert "Löschen" in script
    assert "window.confirm" in script
