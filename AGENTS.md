# AGENTS.md — CivitAI Browser Neo

> Reference for AI coding agents working on this project.  
> Last updated: 2026-04-17  
> Version: v0.8.3

---

## Project Overview

**CivitAI Browser Neo** is a [Stable Diffusion WebUI Forge Neo](https://github.com/Haoming02/sd-webui-forge-classic/tree/neo) extension that lets users browse, download, and manage CivitAI models directly inside the WebUI.  

Key capabilities:
- Browse & search CivitAI with filters (content type, base model, sort, time period, NSFW, exact search)
- High-speed downloads via Aria2 (multi-connection, queue, cancel, hash validation)
- Auto-organization of models into subfolders by base model (SDXL/, Pony/, FLUX/, Wan/, etc.)
- Dashboard with disk-usage stats, top files, orphan detection, CSV/JSON export
- Creator management (favorite ⭐ / ban 🚫)
- Update detection (orange borders on outdated models) with batch update
- Model info overlay with sample images, trigger words, and "Send to txt2img"

This is the **Neo** branch (upstream).  
There is a downstream twin project **sd-civitai-browser-ex** for Automatic1111 / Forge Classic (Gradio 3.x).  
Neo-specific changes must not be blindly ported to EX.

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Runtime | Python 3.x (matching the Forge Neo environment) |
| UI Framework | Gradio 4.40.0+ (breaking difference vs Gradio 3) |
| Host | Forge Neo (by Haoming02) |
| Download Engine | Aria2 1.x (RPC-based, binaries bundled in `aria2/win` and `aria2/lin`) |
| Frontend | Vanilla JavaScript (`javascript/civitai-html.js`) |
| Styling | Custom CSS (`style_html.css`, `style.css`) |

### Python Dependencies (`requirements.txt`)
- `send2trash` — recycle-bin deletion
- `ZipUnicode` — unicode-safe ZIP extraction
- `beautifulsoup4` — HTML parsing for model info
- `packaging` — version comparison
- `pysocks` — proxy support

### Implicit Runtime Dependencies
- `requests` — HTTP client
- `Pillow` (PIL) — image processing
- `gradio` — provided by Forge Neo

---

## Project Structure

```
sd-civitai-browser-neo/
├── install.py                   # Forge dependency-install hook (auto-executed on startup)
├── requirements.txt             # Python dependencies
├── LICENSE                      # MIT
├── README.md                    # Public user-facing documentation (English)
├── AGENTS.local.md              # Private local context (Portuguese, gitignored)
│
├── style.css                    # General UI styles (Gradio component overrides)
├── style_html.css               # Model card / preview / overlay styles
├── _mockup_banner.html          # Design reference / mock-up
│
├── aria2/                       # Download-engine binaries
│   ├── win/aria2.exe
│   └── lin/aria2
│
├── docs/
│   └── PROJECT_LOG.md           # Private dev timeline & backlog (Portuguese, gitignored)
│
├── javascript/
│   ├── civitai-html.js          # Frontend logic (card interaction, tile sizing, overlay, etc.)
│   └── Sortable.min.js          # Drag-and-drop library (not actively used)
│
├── lib/
│   ├── models/                  # JSON metadata cache created at runtime (gitignored)
│   └── utils/                   # Reserved for future utilities
│
└── scripts/                     # Python backend (loaded automatically as Forge extension)
    ├── civitai_gui.py           # Gradio UI definition: tabs, callbacks, settings persistence
    ├── civitai_api.py           # CivitAI REST API client, HTML card generation, validation helpers
    ├── civitai_download.py      # Aria2 RPC integration, queue manager, SHA256 verification
    ├── civitai_file_manage.py   # File operations: organize, delete, backup, dashboard, creator mgmt
    ├── civitai_global.py        # Shared global state (gl.init(), download_queue, colors)
    └── download_log.py          # Queue persistence: neo_download_queue.jsonl
```

### Data Flow

```
User (Gradio UI)
    ↓
civitai_gui.py  →  Gradio callbacks
    ↓
civitai_api.py  ←→  CivitAI REST API
    ↓
civitai_download.py  ←→  Aria2 RPC
    ↓
civitai_file_manage.py  →  Filesystem
    ↓
lib/models/*.json          Metadata cache
```

---

## Build and Run Commands

### Installation (inside Forge Neo)
1. Extensions → Install from URL
2. Paste: `https://github.com/eduardoabreu81/sd-civitai-browser-neo`
3. Install and reload the WebUI

### Manual Installation
```bash
cd extensions/
git clone https://github.com/eduardoabreu81/sd-civitai-browser-neo
cd sd-civitai-browser-neo
pip install -r requirements.txt
```

### Build Process
There is **no build step**.  
Forge Neo automatically executes `install.py` on startup, which pip-installs anything missing from `requirements.txt`.

### Debug / Development Settings
Enable these inside Forge Neo Settings, then reload the UI:
- `civitai_debug_prints` — verbose terminal output
- `civitai_neo_debug_organize` — organization debug prints
- `show_log` — Aria2 RPC log output

---

## Code Style Guidelines

### Language
- **Code, comments, docstrings, and commits:** English
- **Private chat / local docs:** Brazilian Portuguese (per `.github/copilot-instructions.md`)

### Commit Convention
```
type(scope): short description

Types: feat | fix | chore | refactor | docs | test
Scope : python | js | css | readme | ci
```
Examples:
- `feat(python): add Wan I2V/T2V subfolder split`
- `fix(js): correct genInfo paste button selector for Gradio 4`
- `docs: bump to v0.8.3`

### Versioning
- Neo: `vX.Y.Z`
- EX:  `vX.Y.Z-ex`
- `X` = architecture / breaking change
- `Y` = new features (backward-compatible)
- `Z` = bug fixes / stability patches

### Python Conventions
- Import order: (1) stdlib, (2) third-party, (3) WebUI (`modules.*`), (4) extension (`scripts.*`)
- Every module calls `gl.init()` at the top level (legacy global-state initialization)
- Use `from scripts.civitai_global import print, debug_print` for prefixed terminal output
- Prefer `pathlib.Path` for new path handling; legacy code still uses `os.path`
- Docstrings are concise and in English

### JavaScript Conventions
- Vanilla JS only; no frameworks
- `gradioApp().querySelector(...)` is used to reach Gradio-generated DOM nodes
- `updateInput(element)` is the Gradio helper to trigger value changes

---

## Testing Instructions

**There is no formal test framework.**  
All testing is manual through the WebUI:

1. Start Forge Neo with the extension loaded.
2. Open the **CivitAI Browser** tab.
3. Exercise the feature you changed (search, download, organize, dashboard, delete, etc.).
4. Check the terminal for `debug_print` output if applicable.
5. Verify no regressions in related tabs (Browser, Download Manager, Update Models, Dashboard).

**Recommended manual smoke-test matrix:**
- Browse → search → filter by base model → click a card
- Download a model → verify progress → verify SHA256 validation
- Queue multiple items → cancel one → clear all
- Update Models → scan → organize → validate → undo
- Dashboard → generate → export CSV/JSON

---

## Security Considerations

### File Operations
- **Never delete permanently by default.** Always use `send2trash()` or create an automatic backup first.
- **Filename sanitization is mandatory** before saving (`_api.sanitize_filename()`). Illegal characters are stripped and length is capped.
- **Associated files must travel together:** when moving/deleting a `.safetensors` file, always include its `.json`, `.png`, and `.txt` sidecars.

### Network / Download
- SHA256 hash is verified after every download. If the hash mismatches, the file is deleted and an error is raised.
- Aria2 RPC runs with `check-certificate=false` and a fixed secret (`R7T5P2Q9K6`) on port `24000`. This is a local-only service, but be aware if exposing the WebUI externally.
- `urllib3` insecure-request warnings are suppressed globally (`gl.init()`). This is legacy behavior required for some proxy/proxy-less setups.
- CivitAI API key can be configured for early-access or private models. The key is stored through Forge's standard settings system (`opts.civitai_api_key`).

### Path Traversal
- `contenttype_folder()` can return `None` → callers must guard against it.
- Upscaler and embedding folder resolution has complex fallback logic because Neo uses different paths than Classic (`models/embeddings/` vs `embeddings/`, `models/ESRGAN/` vs separate subfolders).

---

## Critical Architectural Invariants

1. **Gradio 4+ Only**  
   Neo targets Gradio 4.40.0+. APIs differ from Gradio 3 (e.g., `gr.update()` syntax, `queue` parameter handling). Do not port code from the EX project without validating compatibility.

2. **Forge Neo Folder Layout**  
   - Embeddings: `models/embeddings/` (Neo) vs `embeddings/` (Classic)
   - Upscalers: `models/ESRGAN/` (Neo unifies everything)
   - Auto-detection is implemented in `civitai_file_manage.py` (`_get_embeddings_folder()`, `_upscaler_folder_resolver()`).

3. **Global State (`civitai_global.py`)**  
   - `gl.init()` initializes module-level mutable variables (`download_queue`, `json_data`, etc.).
   - This is a known anti-pattern inherited from the upstream fork. **Do not refactor without a migration plan** — many callbacks depend on it.
   - Not thread-safe; `_not_downloading` event in `civitai_download.py` provides minimal synchronization.

4. **Aria2 RPC Lifecycle**  
   - Start: `start_aria2_rpc()` in `civitai_download.py`
   - Auto-reconnect if the RPC crashes
   - Port `24000`, secret `R7T5P2Q9K6`
   - Process tracking via `aria2/_` → `aria2/running` files

5. **Queue Persistence**  
   - Stored in `config_states/neo_download_queue.jsonl`
   - States: `queued → downloading → completed | cancelled | failed | dismissed`
   - A restore banner appears on UI load if orphaned `queued` entries exist

6. **Organization Backups**  
   - `config_states/civitai_organization_backups.json` keeps the last 5 backups
   - Every organize/fix operation appends a backup entry before moving files

7. **Runtime Artifacts (never commit)**  
   - `config_states/` — Forge settings + extension state
   - `lib/models/` — JSON metadata cache + checkpoint hash registry
   - `aria2/running`, `aria2/_` — process lock files
   - `favoriteCreators.txt`, `bannedCreators.txt` — creator lists

---

## Twin Project Sync Notes

- **NEO is upstream** — develop features here first.
- **EX is downstream** — generic bugfixes may be synced to EX, but Neo-specific code must not flow automatically.
- Avoid hard Gradio 4+ dependencies if a feature is critical and likely to be ported to EX.
- Internal sync tags/rules must stay in gitignored files only (`.github/internal-sync-rules.md`, `docs/INTERNAL_SYNC_RULES.md`).

---

## Post-Change Checklist

When you finish a non-trivial change:
1. Update `docs/PROJECT_LOG.md` with a dated entry (template in `.github/copilot-instructions.md`).
2. If architecture or features changed, update `AGENTS.local.md`.
3. If user-visible, suggest updating `README.md` (What's New, Changelog, Roadmap).
4. Ensure `config_states/` and `lib/models/` changes are **not** committed.
5. Run a manual smoke test in the WebUI.

---

## Useful References

- `README.md` — public features, changelog, roadmap
- `AGENTS.local.md` — private local context (Portuguese)
- `docs/PROJECT_LOG.md` — dev timeline and decisions (Portuguese)
- `.github/copilot-instructions.md` — AI workflow rules and commit conventions
- `scripts/civitai_global.py` — global state and color constants
- `scripts/download_log.py` — queue persistence schema and helpers
