from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_wifi_installer_uses_the_documented_fixed_network() -> None:
    installer = read("scripts/install-admin-wifi.sh")

    assert 'profile_name="zunder-zapfe-ap"' in installer
    assert 'wifi_ssid="ZUNDER_ZAPFE"' in installer
    assert 'wifi_interface="wlan0"' in installer
    assert 'wifi_address="10.42.0.1/24"' in installer
    assert "ipv4.method shared" in installer
    assert "ipv4.never-default yes" in installer
    assert "ipv6.method disabled" in installer


def test_wifi_installer_protects_credentials_and_existing_connections() -> None:
    installer = read("scripts/install-admin-wifi.sh")

    assert 'read -r -s -p "Neuer WPA-Schluessel' in installer
    assert 'install -m 0600 "${temporary_profile}" "${profile_path}"' in installer
    assert '[[ "${confirmation}" == "ZUNDER_ZAPFE" ]]' in installer
    assert "psk=${wifi_psk}" in installer
    assert "nmcli device wifi hotspot" not in installer
    assert "password" not in installer.lower()


def test_pi_installer_installs_wifi_dependencies_and_self_contained_helper() -> None:
    installer = read("scripts/install-pi.sh")

    assert "network-manager iw nginx-light" in installer
    assert "/usr/local/sbin/zunder-zapfe-admin-wifi" in installer
    assert "/usr/local/sbin/zunder-zapfe-wifi-mode" in installer
    assert "zunder-zapfe-networkmanager.rules" in installer
    assert "/usr/local/share/zunder-zapfe/zunder-zapfe-admin.conf" in installer
    assert "sudo zunder-zapfe-admin-wifi" in installer


def test_wifi_mode_helper_only_activates_existing_profiles() -> None:
    helper = read("scripts/wifi-mode.sh")
    policy = read("deploy/polkit/zunder-zapfe-networkmanager.rules.in")

    assert 'action="${1:-status}"' in helper
    assert "connection show" in helper
    assert "connection up id" in helper
    assert "connection add" not in helper
    assert "device wifi connect" not in helper
    assert "psk" not in helper.lower()
    assert "org.freedesktop.NetworkManager.network-control" in policy
    assert "org.freedesktop.NetworkManager.wifi.share.protected" in policy
    assert "org.freedesktop.NetworkManager.settings.modify.system" in policy
    assert "org.freedesktop.NetworkManager.wifi.share.open" not in policy
    assert "org.freedesktop.NetworkManager.enable-disable-network" not in policy


def test_nginx_exposes_only_the_smartphone_admin_surface() -> None:
    nginx = read("deploy/nginx/zunder-zapfe-admin.conf")

    assert "allow 10.42.0.0/24;" in nginx
    assert "location /api/web-auth/" in nginx
    assert "location /api/web-admin/" in nginx
    assert "location = /api/health" in nginx
    assert "location = /admin" in nginx
    assert "location /static/admin-" in nginx
    assert "/api/admin/" not in nginx
    assert "/api/tap/" not in nginx
    assert "/api/simulator/" not in nginx


def test_pi_verification_checks_configured_admin_wifi() -> None:
    verification = read("scripts/pi-verify.sh")

    assert "6/7 Admin-WLAN" in verification
    assert "zunder-zapfe-wifi-mode status" in verification
    assert "mode=ap" in verification
    assert "mode=client" in verification
    assert "ZUNDER_ZAPFE" in verification
    assert "10.42.0.1" in verification
    assert "http://10.42.0.1/api/health" in verification
    assert "http://127.0.0.1:8000/static/system.js" in verification


def test_deployment_detects_branch_switches_and_missing_runtime_dependencies() -> None:
    deployment = read("scripts/deploy-update.sh")

    assert 'deployed_revision_path="/var/lib/zunder-zapfe/deployed-revision"' in deployment
    assert "import alembic, fastapi, pwdlib, smartcard, sqlalchemy, uvicorn" in deployment
    assert '"${deployed_revision}" "${new_revision}"' in deployment
    assert 'printf \'%s\\n\' "${new_revision}" >"${deployed_revision_path}"' in deployment
