# Agent guide for Zunder Zapfe

This file applies to the complete repository. It provides stable project
context for coding agents; contributor-specific identities and local tool
preferences do not belong here.

## Read first

1. `requirements/anforderungskatalog.txt` for accepted product behaviour.
2. `docs/README.md` for the documentation map and sources of truth.
3. `docs/project-status.md` before assuming a component is implemented.
4. The relevant executable interface before changing its documentation.

## Architecture boundaries

- Web code calls the local HTTP API; it never controls hardware or SQLite
  directly.
- `TapController` is the only component allowed to coordinate valve and flow
  operations.
- `TapService` connects NFC identity, tap control, active event/keg context and
  persistence.
- Hardware implementations satisfy the protocols in
  `src/zunder_zapfe/hardware/interfaces.py`.
- Concrete GPIO numbers, electrical levels and libraries remain adapter
  configuration until hardware decisions are approved.
- The default runtime uses real ACR122U NFC and simulated valve, flow meter and
  emergency stop.

## Safety and data invariants

- Start, stop, faults and shutdown must leave the valve closed.
- Safety locks stay latched until a valid admin-card reset; restoring an input
  alone must not resume pouring.
- Volume is stored in millilitres, prices in cents per litre and amounts in
  cents. Do not introduce floating-point billing.
- Completed tap bookings are immutable. Corrections require a future explicit
  domain operation, never an update or delete.
- Schema changes require an Alembic migration. Never edit a deployed SQLite
  database as an application workflow.
- The application remains offline-capable and bound to loopback by default.

## Secrets and local data

Never commit credentials, private keys, environment files, real NFC UIDs,
database files, backups or logs. Use `config/web.env.example` and obvious demo
identifiers. Do not add personal agent names, emails or commit identities to
repository instructions.

## Development commands

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install --editable ".[dev,debug]"
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m ruff format --check src tests scripts
.\.venv\Scripts\python.exe -m pytest
```

Raspberry Pi/Linux:

```bash
.venv/bin/python -m pip install --editable '.[dev,debug]'
.venv/bin/python -m ruff check src tests scripts
.venv/bin/python -m ruff format --check src tests scripts
.venv/bin/python -m pytest
```

Do not use `sudo pip`. The Pi installer performs privileged system setup but
runs repository-local Python installation as the repository user.

## Change rules

- Work on a short branch; `main` changes only through pull requests.
- Preserve requirement IDs and reference affected IDs in tests, commits or PRs
  when applicable.
- Interface changes require implementation, tests, human-readable contract and
  generated contract updates in one PR.
- Regenerate `docs/interfaces/openapi.json` after HTTP contract changes with
  `python scripts/export_openapi.py`.
- Add a migration and migration test for persistence schema changes.
- Implement hardware-contract extensions in simulators before real adapters.
- Keep simulator-only HTTP routes disabled by default and clearly marked.

## Definition of done

- Relevant requirements and open decisions are identified.
- Safety invariants and architecture boundaries remain intact.
- Tests, Ruff and documentation checks pass.
- Human and machine-readable interfaces agree.
- Operational documentation reflects deployment impact.
- The diff contains no secret, personal runtime data or generated database.
