"""Background monitor for the USB-connected ACR122U NFC reader."""

from __future__ import annotations

import threading
from dataclasses import asdict, dataclass

try:
    from smartcard.System import readers
except ImportError:  # The application must remain diagnosable without PC/SC.
    readers = None


@dataclass(frozen=True)
class NfcStatus:
    state: str
    reader: str | None = None
    uid: str | None = None
    detail: str | None = None


class NfcMonitor:
    """Poll PC/SC without blocking FastAPI request handling."""

    def __init__(self, poll_interval: float = 0.5) -> None:
        self._poll_interval = poll_interval
        self._status = NfcStatus(state="starting", detail="NFC-Dienst wird gestartet")
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
        if self._thread:
            self._thread.join(timeout=2)

    def snapshot(self) -> dict[str, str | None]:
        with self._lock:
            return asdict(self._status)

    def _set_status(self, status: NfcStatus) -> None:
        with self._lock:
            self._status = status

    def _run(self) -> None:
        if readers is None:
            self._set_status(
                NfcStatus(state="unavailable", detail="Python-PC/SC-Unterstuetzung fehlt")
            )
            return

        while not self._stop.is_set():
            try:
                available_readers = readers()
                acr_readers = [reader for reader in available_readers if "ACR122" in str(reader)]
                if not acr_readers:
                    self._set_status(
                        NfcStatus(state="disconnected", detail="Kein ACR122U erkannt")
                    )
                else:
                    self._read_uid(acr_readers[0])
            except Exception as error:  # PC/SC errors vary between driver versions.
                self._set_status(NfcStatus(state="error", detail=str(error)))

            self._stop.wait(self._poll_interval)

    def _read_uid(self, reader: object) -> None:
        reader_name = str(reader)
        try:
            connection = reader.createConnection()
            connection.connect()
            uid_bytes, sw1, sw2 = connection.transmit([0xFF, 0xCA, 0x00, 0x00, 0x00])
            if (sw1, sw2) != (0x90, 0x00):
                raise RuntimeError(f"UID-Abfrage fehlgeschlagen: {sw1:02X}{sw2:02X}")
            uid = "".join(f"{byte:02X}" for byte in uid_bytes)
            self._set_status(NfcStatus(state="card", reader=reader_name, uid=uid))
        except Exception as error:
            # No card in the RF field is the normal idle state. PC/SC backends
            # unfortunately expose this through driver-specific exceptions.
            detail = str(error).lower()
            no_card_markers = ("no smart card", "no card", "removed card", "0x8010000c")
            if any(marker in detail for marker in no_card_markers):
                self._set_status(NfcStatus(state="ready", reader=reader_name))
            else:
                self._set_status(NfcStatus(state="error", reader=reader_name, detail=str(error)))


nfc_monitor = NfcMonitor()
