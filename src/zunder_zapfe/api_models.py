"""Typed HTTP request and response contracts for the local web API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PortionRequest(BaseModel):
    target_volume_ml: int = Field(gt=0)


class SimulatedCardRequest(BaseModel):
    uid: str = Field(min_length=4, max_length=80)


class SimulatedPulsesRequest(BaseModel):
    count: int = Field(gt=0)


class ErrorResponse(BaseModel):
    detail: str


class HealthResponse(BaseModel):
    application: str
    status: str
    version: str
    build: str
    revision: str
    server_time: str


class NfcStatusResponse(BaseModel):
    state: str
    reader: str | None = None
    uid: str | None = None
    detail: str | None = None
    simulated: bool


class ValveStatusResponse(BaseModel):
    is_open: bool
    available: bool
    simulated: bool
    detail: str | None = None


class FlowStatusResponse(BaseModel):
    pulse_count: int
    measuring: bool
    last_pulse_at: float | None = None
    available: bool
    simulated: bool
    detail: str | None = None


class EmergencyStopStatusResponse(BaseModel):
    active: bool
    available: bool
    simulated: bool
    detail: str | None = None


class HardwareStatusResponse(BaseModel):
    nfc: NfcStatusResponse
    valve: ValveStatusResponse
    flow_meter: FlowStatusResponse
    emergency_stop: EmergencyStopStatusResponse


class BookingSummaryResponse(BaseModel):
    id: int
    measured_volume_ml: int
    amount_cents: int
    kind: str
    completion: str


class TapStatusResponse(BaseModel):
    state: str
    user_id: str | None
    is_admin: bool
    valve_open: bool
    measured_pulses: int
    target_pulses: int | None
    measured_volume_ml: int
    target_volume_ml: int | None
    top_up_remaining_ms: int | None
    safety_reason: str | None
    user_display_name: str | None
    special_portion_ml: int | None
    persistence_error: str | None
    last_booking: BookingSummaryResponse | None


class SessionStatusResponse(BaseModel):
    user_id: str | None
    user_display_name: str | None
    is_admin: bool
    special_portion_ml: int | None


class TapOptionsResponse(BaseModel):
    standard_portions_ml: list[int]
    special_portion_ml: int | None
    session_timeout_seconds: int
    manual_press_debounce_ms: int
    manual_maximum_pour_seconds: int
    debug_flow_watchdog_disabled: bool


class PourRecordResponse(BaseModel):
    sequence: int
    kind: str
    user_id: str
    measured_pulses: int
    target_pulses: int | None
    completion: str
    chargeable: bool


class ConsumptionResponse(BaseModel):
    event_id: int
    user_id: int
    booking_count: int
    measured_volume_ml: int
    amount_cents: int


class KegStatusResponse(BaseModel):
    event_id: int
    event_name: str
    beverage_id: int
    beverage_name: str
    keg_id: int
    initial_volume_ml: int
    price_per_liter_cents: int
    remaining_volume_ml: int
