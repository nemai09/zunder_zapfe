"""Run one timed simulator pour against an already running alpha backend."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from zunder_zapfe.backend.tap_service import FlowCalibration


class SmokeTestFailed(RuntimeError):
    """Raised when the backend does not complete the expected alpha flow."""


class JsonClient(Protocol):
    def request_json(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]: ...


class HttpJsonClient:
    """Small standard-library JSON client so the deployed command needs no extra dependency."""

    def __init__(self, base_url: str, *, timeout_seconds: float = 5) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def request_json(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        body = json.dumps(payload).encode() if payload is not None else None
        request = Request(
            f"{self._base_url}{path}",
            data=body,
            method=method,
            headers={"Content-Type": "application/json"} if body is not None else {},
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:  # noqa: S310
                response_body = response.read()
        except HTTPError as error:
            detail = error.read().decode(errors="replace")
            raise SmokeTestFailed(
                f"{method} {path} returned HTTP {error.code}: {detail}"
            ) from error
        except URLError as error:
            raise SmokeTestFailed(
                f"Backend at {self._base_url} is unavailable: {error.reason}"
            ) from error

        if not response_body:
            return {}
        try:
            decoded = json.loads(response_body)
        except json.JSONDecodeError as error:
            raise SmokeTestFailed(f"{method} {path} returned invalid JSON") from error
        if not isinstance(decoded, dict):
            raise SmokeTestFailed(f"{method} {path} returned an unexpected JSON value")
        return decoded


@dataclass(frozen=True)
class SmokeTestResult:
    user_id: str
    booking_id: int
    measured_volume_ml: int
    amount_cents: int
    remaining_volume_ml: int
    final_state: str


def _integer(response: dict[str, Any], field: str, endpoint: str) -> int:
    value = response.get(field)
    if not isinstance(value, int) or isinstance(value, bool):
        raise SmokeTestFailed(f"{endpoint} did not return integer field {field!r}")
    return value


def run_smoke_test(
    client: JsonClient,
    *,
    target_volume_ml: int = 500,
    pulse_count: int | None = None,
    pulses_per_liter: int = 500,
) -> SmokeTestResult:
    """Create and verify one booking through the public HTTP API."""
    if target_volume_ml <= 0:
        raise ValueError("Target volume must be greater than zero")
    calibration = FlowCalibration(pulses_per_liter=pulses_per_liter)
    actual_pulse_count = (
        calibration.target_pulses(target_volume_ml) if pulse_count is None else pulse_count
    )
    if actual_pulse_count <= 0:
        raise ValueError("Pulse count must be greater than zero")

    session = client.request_json("GET", "/api/session/status")
    user_id = session.get("user_id")
    if not isinstance(user_id, str) or not user_id:
        raise SmokeTestFailed("Present a known NFC card before starting the smoke test")

    tap = client.request_json("GET", "/api/tap/status")
    if tap.get("state") != "authenticated":
        state = tap.get("state", "unknown")
        raise SmokeTestFailed(f"Tap must be authenticated before the test; current state: {state}")

    consumption_before = client.request_json("GET", "/api/consumption/current")
    keg_before = client.request_json("GET", "/api/keg/current")

    started = client.request_json(
        "POST", "/api/tap/portion", {"target_volume_ml": target_volume_ml}
    )
    if started.get("state") != "portion_pouring":
        raise SmokeTestFailed("Backend did not enter portion_pouring")

    completed = client.request_json(
        "POST", "/api/simulator/flow/pulses", {"count": actual_pulse_count}
    )
    if completed.get("state") != "top_up_available":
        state = completed.get("state", "unknown")
        reason = completed.get("safety_reason")
        raise SmokeTestFailed(f"Pour did not complete; state: {state}, reason: {reason}")

    booking = completed.get("last_booking")
    if not isinstance(booking, dict) or booking.get("completion") != "target_reached":
        raise SmokeTestFailed("Backend did not return a completed target booking")

    consumption_after = client.request_json("GET", "/api/consumption/current")
    keg_after = client.request_json("GET", "/api/keg/current")
    measured_volume_ml = _integer(booking, "measured_volume_ml", "/api/tap/status")
    amount_cents = _integer(booking, "amount_cents", "/api/tap/status")
    expected_volume_ml = calibration.measured_volume_ml(actual_pulse_count)

    checks = {
        "booking measured volume": measured_volume_ml == expected_volume_ml,
        "consumption booking count": _integer(
            consumption_after, "booking_count", "/api/consumption/current"
        )
        == _integer(consumption_before, "booking_count", "/api/consumption/current") + 1,
        "consumption measured volume": _integer(
            consumption_after, "measured_volume_ml", "/api/consumption/current"
        )
        == _integer(consumption_before, "measured_volume_ml", "/api/consumption/current")
        + measured_volume_ml,
        "consumption amount": _integer(
            consumption_after, "amount_cents", "/api/consumption/current"
        )
        == _integer(consumption_before, "amount_cents", "/api/consumption/current") + amount_cents,
        "keg remaining volume": _integer(keg_after, "remaining_volume_ml", "/api/keg/current")
        == _integer(keg_before, "remaining_volume_ml", "/api/keg/current") - measured_volume_ml,
    }
    failed_checks = [name for name, passed in checks.items() if not passed]
    if failed_checks:
        raise SmokeTestFailed("Persistence verification failed: " + ", ".join(failed_checks))

    return SmokeTestResult(
        user_id=user_id,
        booking_id=_integer(booking, "id", "/api/tap/status"),
        measured_volume_ml=measured_volume_ml,
        amount_cents=amount_cents,
        remaining_volume_ml=_integer(keg_after, "remaining_volume_ml", "/api/keg/current"),
        final_state=str(completed["state"]),
    )


def run() -> None:
    """Command-line entry point for the alpha integration check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--target-volume-ml", type=int, default=500)
    parser.add_argument("--pulse-count", type=int)
    parser.add_argument(
        "--pulses-per-liter",
        type=int,
        default=int(os.environ.get("ZUNDER_ZAPFE_PULSES_PER_LITER", "500")),
    )
    arguments = parser.parse_args()
    try:
        result = run_smoke_test(
            HttpJsonClient(arguments.base_url),
            target_volume_ml=arguments.target_volume_ml,
            pulse_count=arguments.pulse_count,
            pulses_per_liter=arguments.pulses_per_liter,
        )
    except (SmokeTestFailed, ValueError) as error:
        print(f"Smoke test failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error

    print("Smoke test passed.")
    print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    run()
