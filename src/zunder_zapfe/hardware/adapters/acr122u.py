"""PC/SC adapter for the USB-connected ACR122U NFC reader."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Protocol, Self

from zunder_zapfe.hardware.models import NfcStatus

try:
    from smartcard.CardRequest import CardRequest as PcscCardRequest
    from smartcard.Exceptions import CardRequestTimeoutException as PcscTimeoutError
    from smartcard.System import readers as pcsc_readers
except ImportError:  # The application must remain diagnosable without PC/SC.
    PcscCardRequest = None
    PcscTimeoutError = TimeoutError
    pcsc_readers = None

DEFAULT_EVENT_WAIT_TIMEOUT_SECONDS = 1.0
DEFAULT_RECONNECT_INTERVAL_SECONDS = 1.0
UID_COMMAND = [0xFF, 0xCA, 0x00, 0x00, 0x00]


class _CardConnection(Protocol):
    def connect(self) -> None: ...

    def transmit(self, command: list[int]) -> tuple[list[int], int, int]: ...

    def disconnect(self) -> None: ...


class _Card(Protocol):
    reader: object
    atr: list[int]

    def createConnection(self) -> _CardConnection: ...


class _CardEventRequest(Protocol):
    def __enter__(self) -> Self: ...

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> object: ...

    def waitforcardevent(self) -> list[_Card]: ...


CardRequestFactory = Callable[..., _CardEventRequest]
ReaderProvider = Callable[[], list[object]]


class Acr122uNfcReader:
    """Wait for PC/SC card events without repeatedly opening the reader."""

    def __init__(
        self,
        event_wait_timeout_seconds: float = DEFAULT_EVENT_WAIT_TIMEOUT_SECONDS,
        reconnect_interval_seconds: float = DEFAULT_RECONNECT_INTERVAL_SECONDS,
        *,
        card_request_factory: CardRequestFactory | None = None,
        reader_provider: ReaderProvider | None = None,
    ) -> None:
        if event_wait_timeout_seconds <= 0:
            raise ValueError("NFC event wait timeout must be greater than zero")
        if reconnect_interval_seconds <= 0:
            raise ValueError("NFC reconnect interval must be greater than zero")
        self._event_wait_timeout_seconds = event_wait_timeout_seconds
        self._reconnect_interval_seconds = reconnect_interval_seconds
        self._card_request_factory = card_request_factory or PcscCardRequest
        self._reader_provider = reader_provider or pcsc_readers
        self._status = NfcStatus(state="starting", detail="NFC-Dienst wird gestartet")
        self._present_card_identity: tuple[str, tuple[int, ...]] | None = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="nfc-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=self._event_wait_timeout_seconds + 1)

    def snapshot(self) -> NfcStatus:
        with self._lock:
            return self._status

    def _set_status(self, status: NfcStatus) -> None:
        with self._lock:
            self._status = status

    def _run(self) -> None:
        if self._card_request_factory is None or self._reader_provider is None:
            self._set_status(
                NfcStatus(state="unavailable", detail="Python-PC/SC-Unterstuetzung fehlt")
            )
            return

        while not self._stop.is_set():
            try:
                with self._card_request_factory(
                    timeout=self._event_wait_timeout_seconds
                ) as request:
                    self._monitor_events(request)
            except Exception as error:  # PC/SC errors vary between driver versions.
                if self._stop.is_set():
                    return
                self._present_card_identity = None
                self._set_status(NfcStatus(state="error", detail=str(error)))
                self._stop.wait(self._reconnect_interval_seconds)

    def _monitor_events(self, request: _CardEventRequest) -> None:
        self._refresh_reader_status()
        while not self._stop.is_set():
            try:
                cards = request.waitforcardevent()
            except PcscTimeoutError:
                self._refresh_reader_status()
                continue
            self._process_card_event(cards)

    def _acr_reader_names(self) -> list[str]:
        if self._reader_provider is None:
            return []
        return [str(reader) for reader in self._reader_provider() if "ACR122" in str(reader)]

    def _refresh_reader_status(self) -> None:
        reader_names = self._acr_reader_names()
        if not reader_names:
            self._present_card_identity = None
            self._set_status(NfcStatus(state="disconnected", detail="Kein ACR122U erkannt"))
            return

        status = self.snapshot()
        if status.state in {"starting", "disconnected", "error"}:
            self._set_status(NfcStatus(state="ready", reader=reader_names[0]))

    def _process_card_event(self, cards: list[_Card]) -> None:
        acr_cards = [card for card in cards if "ACR122" in str(card.reader)]
        if not acr_cards:
            self._present_card_identity = None
            reader_names = self._acr_reader_names()
            if reader_names:
                self._set_status(NfcStatus(state="ready", reader=reader_names[0]))
            else:
                self._set_status(NfcStatus(state="disconnected", detail="Kein ACR122U erkannt"))
            return

        card = acr_cards[0]
        identity = (str(card.reader), tuple(card.atr))
        if identity == self._present_card_identity and self.snapshot().state == "card":
            return

        if self._read_uid(card):
            self._present_card_identity = identity

    def _read_uid(self, card: _Card) -> bool:
        reader_name = str(card.reader)
        connection: _CardConnection | None = None
        try:
            connection = card.createConnection()
            if connection is None:
                raise RuntimeError("PC/SC konnte keine Kartenverbindung erstellen")
            connection.connect()
            uid_bytes, sw1, sw2 = connection.transmit(UID_COMMAND)
            if (sw1, sw2) != (0x90, 0x00):
                raise RuntimeError(f"UID-Abfrage fehlgeschlagen: {sw1:02X}{sw2:02X}")
            uid = "".join(f"{byte:02X}" for byte in uid_bytes)
            self._set_status(NfcStatus(state="card", reader=reader_name, uid=uid))
            return True
        except Exception as error:
            detail = str(error).lower()
            no_card_markers = ("no smart card", "no card", "removed card", "0x8010000c")
            if any(marker in detail for marker in no_card_markers):
                self._present_card_identity = None
                self._set_status(NfcStatus(state="ready", reader=reader_name))
                return False
            self._set_status(NfcStatus(state="error", reader=reader_name, detail=str(error)))
            raise
        finally:
            if connection is not None:
                try:
                    connection.disconnect()
                except Exception:
                    pass
