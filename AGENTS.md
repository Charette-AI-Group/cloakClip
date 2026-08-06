# AGENTS.md — Solo Qt GUI Python Projects

This repository is maintained by one developer with AI assistance.
Optimize for clarity, safe refactoring, and a GUI that stays responsive.

## Project type

- Python desktop GUI app using **PySide6** (Qt 6).
- Solo project: no team processes, but keep structure so humans and agents can navigate the code later.

---

# This app: CloakClip

Encrypts and decrypts text in the clipboard with a shared password. Wire-compatible with the original `encrypt.ps1` / `decrypt.ps1` scripts: AES-256-CBC, key = SHA-256 of the password, random 16-byte IV prepended, Base64.

The interesting part is not the crypto — it is keeping a *decrypted* secret from outliving its use. On Windows that means keeping it out of clipboard history (Win+V) and cloud sync. Read `README.md` for the user-facing behaviour before changing anything.

**Status:** Windows is fully supported. macOS builds and launches (CI proves it every push) but has **no clipboard protections** — it gets the generic no-op backend, which reports every protection as unavailable rather than pretending.

## Notes for a macOS session

Everything below is the remaining work. It was scoped from Windows, so treat macOS specifics as *leads to verify*, not facts.

### Already settled on macOS — do not re-derive

A session on real hardware established the following. The three tasks below are still open; this is the ground you start from.

- **The app runs, and the suite runs.** `pytest` on macOS is 102 passed, 20 skipped, 0 failed, in about 12 seconds. Before that work it never finished at all.
- **Theme switching works** — `applyTheme` yields `ColorScheme.Dark` with palette `#323232` and `ColorScheme.Light` with `#ececec`. No macOS work needed there.
- **Run the suite with no `QT_QPA_PLATFORM` override.** Under `offscreen` the colour scheme reports `Unknown` and the palette never changes, so four theme tests fail for reasons that have nothing to do with the code.
- **Known open defect:** a SIGSEGV during interpreter teardown *after* the app exits, in shiboken's destruction of a `QMimeData` wrapper. Not reproducible on demand — seven attempts are recorded in issue #7 along with the dead ends, so read it before spending time there.

Four defects were found and fixed, every one the same shape: **logic whose correctness silently depended on a Windows-only capability, failing quietly rather than loudly.** A layout loop that only Windows' zero frame padding concealed; a clipboard guard that answered its own write forever because only *marking* could stop it; and two tests asserting Windows-only behaviour. When you add the macOS backend, assume this pattern is still lurking — the absence of a capability tends to turn a terminating condition into a non-terminating one.

### Where the platform line is drawn

| File | Role |
|---|---|
| `services/platform/clipboardBackend.py` | The interface, and a working no-op backend |
| `services/platform/windowsClipboard.py` | Reference implementation — read this first |
| `services/clipboardService.py` | `createBackend()` — the single branch to extend |
| `services/passwordHistoryService.py` | DPAPI store, Windows-only, gated on `dpapiAvailable` |

Qt handles plain clipboard read/write on every platform; only *protection* is platform-specific. Nothing above the service layer should need to change — if you find yourself editing `ui/`, stop and reconsider.

### Task 1 — `services/platform/macClipboard.py`

Implement `ClipboardBackend` with `name = "macos"`:

- **`secretMimeData()`** — the lead is `org.nspasteboard.ConcealedType`, a convention that clipboard managers (Raycast, Alfred, Maccy, Paste) *choose* to honour. Nothing in macOS enforces it, so do not describe it to the user as equivalent to the Windows guarantee. Qt's `application/x-qt-windows-mime;value="…"` trick has no macOS twin, so this likely needs PyObjC talking to `NSPasteboard` directly. If a raw pasteboard write is needed, add an optional hook to the backend interface — do **not** let `NSPasteboard` leak up into `clipboardService` or the UI.
- **`supportsHistory` → `False`.** macOS has no built-in clipboard history. That is genuinely good news: the exposure the Windows code fights does not exist. Leave `clearHistory()` and `deleteHistoryTexts()` as inherited no-ops. **Never fake them.**
- Consequence to raise with the user: the Clipboard tab's **Clear Clipboard & History** button and the session-secret purge become partly meaningless on macOS. Ask before relabelling — do not silently change shared UI text.

### Task 2 — Keychain-backed password history

`passwordHistoryService` stores a JSON list encrypted with DPAPI at `%APPDATA%\CloakClip\passwordHistory.bin`. On macOS use the Keychain (the `keyring` package is the pragmatic route; add it with a `sys_platform == 'darwin'` marker).

Give it the same treatment as the clipboard: a `services/platform/secretStore.py` interface with Windows and macOS implementations, keeping the public API (`loadPasswords`, `rememberPassword`, `clearPasswords`, `maskPassword`) unchanged. A test asserts the stored bytes never contain the plaintext password — keep an equivalent assertion for the Keychain.

### Task 3 — Universal Clipboard

macOS syncs the clipboard to nearby Apple devices. This is a **new exposure with no Windows counterpart**, and it is not currently handled anywhere. Find out whether the concealed marker suppresses it. If you cannot verify it, say so plainly in the README rather than implying protection.

### Verify empirically — this is not optional here

Three Windows features looked correct in code and in tests, and were wrong until probed against the live API:

- Secret marking — proven only by a control/treatment pair checked against the real Win+V history.
- History purging — needed the real API to confirm it deleted the right item and nothing else.
- A theme switch left a tab label invisible (white on white) because styling was rebuilt before Qt delivered the new palette. Tests passed; a screenshot caught it.

So: write throwaway probe scripts, run them, read the output. Screenshot the GUI in both light and dark. Do not report a protection as working because the code looks right.

### Test rules you must respect

`tests/testUi/conftest.py` has autouse fixtures that keep the suite away from real user state: the settings file, the password history, the forced colour scheme, the modal password dialog, and `deleteHistoryTexts`. **Add an equivalent isolation fixture before touching the Keychain** — a test run must never read or write the developer's real Keychain, and a modal dialog must never be able to open and hang the suite.

`tests/platformSkips.py` holds `needsPasswordStore` and `needsSecretMarking`. They gate on the **capability** (`passwordHistoryService.dpapiAvailable`, `clipboardService.backend.supportsSecretMarking`), never on `sys.platform`. Implementing a backend therefore un-skips the matching tests by itself — which also means **they become your acceptance criteria**: land `macClipboard.py` and the four secret-marking tests start running and must pass. Keep any new skip keyed the same way.

A skipped test must still be worth running once it is un-skipped. Three password-history tests used to pass on macOS while proving nothing — with no store, "the file is gone" holds because none was ever written. Each now establishes that the store works before asserting what it claims. If you add a test that a missing capability would satisfy trivially, give it that kind of precondition.

The CI test job runs on `windows-latest`, so macOS work must not break the Windows suite.

### Build and verification

```bash
python tools/buildStandalone.py          # uses the committed cloakClip.spec
./dist/CloakClip.app/Contents/MacOS/CloakClip --selftest report.txt
```

`--selftest` reports the backend and each capability, and exists precisely because these pieces fail *quietly*. Once macOS has real protections, update `expectProtections` in `main.py:runSelfTest` so a macOS build that lost them fails too — right now it only enforces this on Windows.

`.github/workflows/build.yml` builds both platforms on every push and attaches both to a Release on `v*` tags.

### Definition of done

1. `--selftest` on macOS reports `clipboardBackend=macos` and `secretMarking=True`.
2. A decrypted secret copied on macOS does **not** appear in an installed clipboard manager that honours the convention — verified by looking, not assumed.
3. Password history works through the Keychain, with plaintext never recoverable from stored bytes.
4. The README platform section describes what macOS actually does, including the honest limits.
5. The Windows suite is still green in CI.

## Naming conventions (required)

| Item | Style | Example |
|------|-------|---------|
| Source file names | camelCase | `mainWindow.py`, `exportCsvDialog.py` |
| Variables, functions, methods | camelCase | `userName`, `loadSettings()`, `onSaveClicked()` |
| Widget object names | camelCase | `statusLabel`, `openButton`, `filePathEdit` |
| Classes | PascalCase | `MainWindow`, `SettingsService` |
| Constants | camelCase or UPPER_SNAKE | Prefer `maxRecentFiles`; UPPER_SNAKE only for true constants |
| User-visible UI text | Title Case with spaces | `"Open File"`, `"Settings"` (not camelCase in labels users read) |

Do **not** use snake_case for new files or identifiers in this project unless required by a third-party API.

## Architecture (mandatory separation)

| Layer | Location | Allowed | Forbidden |
|-------|----------|---------|-----------|
| Entry | `src/<app>/main.py` | Start `QApplication`, load config, show main window | Business logic, heavy work |
| UI | `src/<app>/ui/` | Widgets, layouts, signals wired to slots | Database calls, file parsing, long loops |
| Services | `src/<app>/services/` | Business rules, I/O, calculations | `QWidget`, `QDialog` imports |
| Models | `src/<app>/models/` | Dataclasses, enums, plain state | Qt widgets |
| Config | `appConfig.py` | Paths, defaults, env/settings load | Feature logic |

**Rule of thumb:** If it does not draw pixels or handle input, it does not belong in `ui/`.

## File size and structure

- Target **≤ 500 lines per file**; split by feature when larger.
- One primary window or dialog per file under `ui/`.
- Methods: prefer **≤ 50 lines**; split when there are distinct steps or branches.
- New features go in a **feature folder** under `services/` and `ui/`, not appended to `mainWindow.py`.

Example for an export CSV feature:

```text
services/exportCsvService.py
ui/dialogs/exportCsvDialog.py
tests/testServices/testExportCsvService.py
```

## Qt GUI rules

1. **Never block the GUI thread.** Use `QThread` + signals, or `QThreadPool` + `QRunnable`, for file I/O, network, and heavy computation.
2. **Main window stays thin.** It composes widgets and connects signals; logic lives in services.
3. **Prefer typed signals** where practical (`Signal(str)`, not bare `Signal()`).
4. **User-facing strings** live in UI layer or `appConfig.py` constants—not scattered magic strings.
5. **Resources** (icons, `.ui`, `.qss`) go in `resources/`; paths defined in `appConfig.py`.

## Python standards

- Python **3.14+**.
- **Type hints** on all public functions and methods.
- **`pyproject.toml`** for dependencies and tooling (ruff, pytest).
- Use **dataclasses** or small classes for structured data—not dict soup.
- Logging via `logging` module; no bare `print()` in library/service code (OK in `main.py` for dev).

## Dependencies

- GUI: `PySide6`
- Testing: `pytest`, `pytest-qt`
- Lint/format: `ruff`

Add new dependencies only when needed; update `pyproject.toml`.

## Testing expectations

- **Services:** unit tests required for non-trivial logic.
- **UI:** smoke tests with `pytest-qt` (window opens, buttons exist, critical paths).
- Do not require 100% coverage; do require tests for bugs once fixed.

## When adding or changing behavior

1. Read `README.md` and this file first.
2. Identify the layer (ui / services / models)—put code in the right folder.
3. If touching UI + logic, implement **service first**, then wire UI.
4. If a file exceeds ~500 lines, **split before** adding more code.
5. Update `README.md` if user-visible flow changes.

## What not to do

- Do not create a single monolithic module with everything inside.
- Do not put SQL, HTTP, or file parsing inside widget classes.
- Do not use `time.sleep()` or long synchronous work on the GUI thread.
- Do not introduce new frameworks unless explicitly requested.
- Do not commit secrets, API keys, or `.env` with real credentials.
- Do not rename files or symbols to snake_case during refactors.

## Refactoring

When the app works but code is messy:

1. Extract services from widgets without changing behavior.
2. Add minimal tests around extracted logic.
3. Split oversized files by feature.
4. Update `README.md` architecture section.
