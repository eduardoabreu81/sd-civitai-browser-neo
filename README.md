<div align="center">
  <img src=".github/logo.png?v=2" alt="CivitAI Browser Neo"/>
</div>

# 🎨 CivitAI Browser Neo

<div align="center">

[![Forge Neo](https://img.shields.io/badge/Forge-Neo-blue)](https://github.com/Haoming02/sd-webui-forge-classic/tree/neo)
[![Gradio](https://img.shields.io/badge/Gradio-4.40.0-orange)](https://gradio.app/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Extension for [Stable Diffusion WebUI Forge - Neo](https://github.com/Haoming02/sd-webui-forge-classic/tree/neo)**

</div>

Modern fork of sd-civitai-browser-plus optimized for Forge Neo with auto-organization features and support for latest model architectures (FLUX, Pony, Illustrious, Wan, Qwen, Z-Image, and more).

---

## 📋 Table of Contents

- [Neo Versioning](#-neo-versioning)
- [What's New](#-whats-new--v063)
- [SD Civitai Browser Neo Release Story](#-sd-civitai-browser-neo-release-story)
- [Roadmap](#%EF%B8%8F-roadmap)
- [Features](#-features)
- [Installation](#-installation)
- [Auto-Organization System](#-auto-organization-system)
- [Dashboard & Statistics](#-dashboard--statistics)
- [Supported Model Types](#-supported-model-types)
- [Credits](#-credits)

---

## 🔢 Neo Versioning

Neo uses semantic versioning with this format:

- `vX.Y.Z`
- `X` = Major updates (breaking changes or major architecture shifts)
- `Y` = Minor updates (new features and UX improvements)
- `Z` = Bug fixes, regressions, and stability patches

Examples:
- `v1.0.0`: First stable major release
- `v0.4.0`: New feature set, backward-compatible
- `v0.4.3`: Bug-fix release on top of `v0.4.x`
- `v0.5.0`: Dashboard upgrade (export, rankings, orphan detection)

---

## 🆕 What's New — v0.6.3

> **Download Reliability Patch** — SHA256 integrity check, batch enqueue API deferral (instant queueing for large batches), thread-safe cancel, and Aria2 auto-reconnect after RPC failures.

- **🔒 SHA256 integrity check** — after every download completes, the file is verified against CivitAI's expected hash; corrupted or truncated files are caught and removed automatically ⭐
- **⚡ Instant batch enqueue** — API metadata calls are now deferred to download time instead of enqueue time; queuing 10 models is now as fast as queuing 1 ⭐
- **🧵 Thread-safe cancel** — `download_cancel` / `download_cancel_all` now use `threading.Event` instead of a busy-wait `while True` loop ⭐
- **🔄 Aria2 auto-reconnect** — if the Aria2 RPC process crashes or becomes unreachable during a download, the extension automatically restarts it and re-adds the download ⭐
- **⚠️ Skipped model feedback** — if a model can't be loaded during batch queueing, a visible error banner appears in the Download Manager instead of silently dropping it

---

## 📖 SD Civitai Browser Neo Release Story

### v0.6.3
> **Theme: Download Reliability Patch** — six targeted fixes to the download pipeline: integrity verification, fast batch queueing, thread-safe cancel, aria2 resilience, skipped-model UI feedback, and a `from_batch` path mutation bug.

- [x] SHA256 post-download integrity check — `hashlib.sha256` computed in 1 MB chunks after `thread.join()`; mismatch → `gl.download_fail = True` + progress bar message; corrupt files cleaned up automatically
- [x] Lazy API fetch (`_api_ready` flag) — `create_model_item` no longer calls `update_model_versions` / `update_model_info` at enqueue time; both are deferred to `download_create_thread` just before the download starts; reduces batch enqueue from O(2N) API calls to 0, moving them to per-download time
- [x] `threading.Event _not_downloading` — replaces busy-wait `while True / time.sleep(0.5)` in `download_cancel` and `download_cancel_all`; event is cleared on download start, set on download finish; cancel functions use `wait(timeout=60)`
- [x] Aria2 auto-reconnect — in the status-polling `except` block, if retries remain: call `start_aria2_rpc()`, sleep 3 s, re-add the URI via `aria2.addUri`, rebind `gid`; printed message on reconnect
- [x] Skipped model feedback — `selected_to_queue` collects `skipped_names`; if any exist, an error bar is injected into the Download Manager HTML listing the affected model names
- [x] `from_batch` path mutation fix — `item['install_path']` is no longer overwritten; replaced by local `effective_install_path = item['existing_path'] if item['from_batch'] else item['install_path']`

### v0.6.2
> **Theme: Queue Persistence + Restore Banner** — server-side JSONL log captures every queued and active download; a restore banner in the Browser tab lets users recover interrupted queues with one click after a RunPod disconnect or browser reload.

- [x] `scripts/download_log.py` — new log module; JSONL schema per entry (`dl_id`, `dl_url`, `model_filename`, `install_path`, `model_name`, `version_name`, `model_sha256`, `model_id`, `status`, `queued_at`, `updated_at`); full entry lifecycle: `queued → downloading → completed / cancelled / failed / dismissed`
- [x] 5 logging hooks in `civitai_download.py`: `log_queued` in `create_model_item`; `log_downloading` at start of `download_create_thread`; `log_completed/cancelled/failed` before queue pop; `log_cancelled` in `remove_from_queue`; `log_all_cancelled` in `download_cancel_all`
- [x] 4 new functions at end of `civitai_download.py`: `get_interrupted_downloads_json` (purges old entries, returns JSON for UI); `dismiss_interrupted_downloads`; `_restore_queue_item` (rebuilds full queue item from log entry via API); `restore_interrupted_to_queue` (re-enqueues all interrupted items, returns standard 6-tuple to kick off normal download chain)
- [x] `civitai_gui.py`: restore banner `gr.HTML` in Browser tab; 3 hidden textboxes (`restore_queue_input`, `restore_action_trigger`, `dismiss_restore_trigger`); `civitai_interface.load()` fires on every page load to populate the banner
- [x] `civitai-html.js`: `initRestoreBanner(json)` renders the banner HTML with item names; `triggerRestoreQueue()` fires the restore chain; `triggerDismissRestore()` marks all entries dismissed

### v0.6.1
> **Theme: Companion Files Banner + Download Reliability** — contextual architecture guidance on download and a Web Worker fix for background-tab download stalling.

- [x] `_COMPANION_NOTES` dict in `civitai_file_manage.py` — per-architecture notes for Wan 2.2 (generic, HN, LN), FLUX, Qwen, Z-Image, Lumina
- [x] `get_companion_banner(base_model, model_filename, model_name)` — returns an HTML warning banner when downloading a model that requires companion files; injected into the download confirmation flow via `civitai_api.py`
- [x] Wan 2.2 HN/LN detection — regex `(?<![A-Z])HN(?![A-Z])` / `LN` on filename + model name selects the correct tailored note (`WAN_HN` / `WAN_LN`)
- [x] Fix: `setDownloadProgressBar()` replaced `setInterval(..., 500)` with `_createWorkerInterval()` — inline Web Worker runs the 500 ms tick in a background thread, unaffected by browser Page Visibility throttling; all four `clearInterval` call sites replaced with `worker.stop()` which also revokes the blob URL

### v0.6.0
> **Theme: Creator Management** — favorite / ban creators with instant JS filtering and persistent `.txt` storage, inspired by [SignalFlagZ/sd-webui-civbrowser](https://github.com/SignalFlagZ/sd-webui-civbrowser).

- [x] `UserInfo` base class + `FavoriteUsers` / `BanUsers` subclasses in `civitai_file_manage.py`
  - Module-level singletons `FavoriteCreators` / `BanCreators`
  - Persistent storage: `favoriteCreators.txt` / `bannedCreators.txt` — comma-separated, 3 names per line
  - `add()` / `remove()` / `get_as_list()` / `get_as_text()` API; `add` auto-deduplicates
- [x] `add_favorite_creator()` / `ban_creator()` / `clear_creator()` — mutually exclusive: favoriting removes the creator from the ban list and vice versa
- [x] `_creator_button_updates()` — returns 4 `gr.update` values to enable/disable the three action buttons and refresh the hidden textbox
- [x] `civitai_api.py`: `get_model_card()` now accepts a `favorite_creators` set; every `<figure>` card gets `data-creator="{username}"` attribute and `civcard-favorite` CSS class when the creator is favorited
- [x] `favorite_creators` set built once per `model_list_html()` call — no per-card file I/O
- [x] `civitai_gui.py`: `👤 Creator Management` accordion between filter row and card grid
  - `creator_name_txt` auto-fills from `model_id.change` by reading `gl.json_data`
  - `⭐ Favorite` / `🚫 Ban` / `↺ Reset` buttons; enabled/disabled state reflects current status
  - `hide_banned_creators` checkbox added to the filter row
  - `banned_creators_list_txt` hidden textbox keeps JS in sync
- [x] `civitai-html.js`: `initBannedCreators()` / `refreshBannedCreators()` / `hideBannedCreators()`
  - Module-scoped `_bannedCreators[]` array updated on every ban/fav action
  - `hideBannedCreators(checked)` queries `[data-creator]` cards and toggles `display:none`
- [x] `style.css`: `.civcard-favorite { box-shadow: 0 0 2px 2px gold }` + `figcaption::after { content: ' ⭐' }`

### v0.5.0
> **Theme: Dashboard as Console** — export, top-file rankings, and optional orphan detection.

- [x] `export_dashboard_csv()` and `export_dashboard_json()` — return file content into hidden Gradio textboxes
- [x] `downloadBlobFile(content, filename, mimeType)` JS helper — creates a Blob URL and fires a browser download without server disk writes
- [x] "Export CSV" and "Export JSON" buttons added to Dashboard tab (always visible; show empty if no scan yet)
- [x] "Top 10 Largest Individual Files" HTML section added below pie chart
- [x] "Top 10 Categories by File Count" HTML section added
- [x] `per_file_records` list collected in all four walk branches during scan (no extra I/O cost)
- [x] "Detect orphan files" checkbox added (default off) — flags `.safetensors` with no `.json` sidecar and `.json` without `modelId`
- [x] Orphan results capped at 50 rows per bucket with `... and N more` overflow row; green ✅ shown when none found
- [x] `last_dashboard_data` module global stores raw data for export between generate and button click
- [x] `_format_size()` extracted as module-level helper (was a local closure in `generate_dashboard_statistics`)

### v0.4.5
> **Theme: Removed Model Failsafe** — graceful degradation when a model has been deleted from CivitAI by its creator.

- [x] When API returns 404, `model_from_sent` checks for a local `.html` sidecar before showing an error
- [x] `inject_removed_banner(html)` helper prepends a red ⚠️ warning banner into the existing cached HTML
- [x] Two code paths covered: SHA256-by-hash 404 (`get_models` → `'Model not found'`) and model-page 404 (`api_response == 'not_found'`)
- [x] `api_error_msg('removed')` added for the case where model was removed and no local cache exists
- [x] `_get_cached_html_stripped` and `_wrap_html_with_css` extracted as DRY helpers

### v0.4.4
> **Theme: Model Overlay Polish + Delete Fix** — LoRA activation syntax, SHA256 display, inline progress bars, delete crash fixed.

- [x] "Add to prompt" now inserts `<lora:filename:1>` prefix for LORA models, followed by trigger words
- [x] SHA256 shown in Version Information block of the model overlay (monospace, click-to-select)
- [x] Validate Organization and Fix Misplaced Files converted to generators — show live progress bars in the UI
- [x] Fix: `show_progress="full"` added to validate and fix GUI bindings
- [x] Fix: `delete_finish` missing `elem_id` caused "Delete function not available" crash on card quick-delete
- [x] Fix: after card quick-delete, card now correctly removes its installed border state
- [x] Fix: `deleteInstalledModel` was passing `model_name_js` to `updateCard` instead of `model_string` — card was never found and updated

### v0.4.3
> **Theme: Organization Validator + Metadata Reliability** — validate + fix misplaced models, guaranteed correct version metadata.

- [x] New "🔍 Validate organization" button in Local Models tab — read-only scan showing correct / misplaced / no-metadata counts with a per-file table
- [x] "✅ Fix misplaced files" button appears after validation — moves only flagged models to correct subfolders, saves a backup first
- [x] "↶ Undo Fix" button appears after fix — reverts changes inline, no need to scroll to Undo section
- [x] NoobAI added as new organization category (folder `NoobAI/`)
- [x] Fix: `"sd version"` in `.json` now saves the raw CivitAI API value, not the normalized folder name — prevents future mis-categorization
- [x] Fix: validator now uses `.api_info.json` as sole source of truth for organization — ignores stale `"sd version": "Other"` in `.json`
- [x] `.api_info.json` now always created on "Save Model Info" — removed opt-in guard, uses `by-hash` endpoint for exact version data
- [x] Auto-fetch `.api_info.json` by SHA256 during validation — saves it on-the-fly and patches `.json` `baseModel` if file is missing
- [x] SHA256 computed on-the-fly in `file_scan` when not cached in `.json` — ensures exact version match via hash instead of fragile filename lookup

### v0.4.2
> **Theme: Bug Fix Patch** — crash fixes, trigger words in overlay, line ending normalization.

- [x] "➕ Add to prompt" button now appears in the model info overlay (CivitAI icon popup in txt2img/img2img)
- [x] Fix: `AttributeError` crash when deleting models with missing `sha256` in `.json`
- [x] Fix: `UnboundLocalError` on `from_batch` when auto-organize was enabled during batch downloads
- [x] Added `.gitattributes` to enforce LF line endings across the codebase

### v0.4.1
> **Theme: UX Polish** — better prompt workflow, safer deletes, complete documentation.

- [x] "➕ Add to prompt" button next to Trained Tags field
- [x] Shift+click append on meta field buttons (Prompt / Negative)
- [x] Setting: move deleted models to OS Trash instead of permanent delete (default ON)
- [x] Filename length capped at 246 UTF-8 bytes (Linux filesystem safety)
- [x] Search settings now persist correctly across restarts (fixed key prefix bug)
- [x] README features section completely rewritten with full documentation

### v0.4.0
> **Theme: Update Intelligence** — smarter update workflow, Dashboard integration, retention policy, audit log.

- [x] Dashboard update summary banner (outdated count per model type, timestamp, per-type pill breakdown)
- [x] Batch update from cards: outdated cards now show checkboxes for multi-select download
- [x] Retention policy for old versions: `keep`, `move to _Trash`, or `replace` (Settings → Model Organization)
- [x] Audit log: `neo_update_audit.jsonl` — records every scan result and retention action

### v0.3.2
- Added **card color legend** bar above the browser grid — always-visible reference for border colors (not installed, installed, update available, Early Access)

### v0.3.1
- Fixed transient DNS failures: `request_civit_api()` now retries up to 3 times with 2 s backoff; persistent failure returns a clear DNS error message in the UI
- Fixed **Model Organization** button disappearing after any scan failure — all action buttons now always restored on `scan_finish()`

### v0.3.0
- Dashboard UX polish completed
- Added **Hide empty categories (0 files)** toggle
- Added scan summary metrics: folders scanned, scan duration, skipped files, read errors
- Improved dashboard state messages for empty selection and no matching files

### v0.2.1
- Standardized Dashboard output to English-only labels and documentation
- Moved dashboard debug logs behind debug mode (`civitai_neo_debug_organize`)
- Fixed dashboard runtime regression (`print()` signature issue in Forge context)

### v0.2.0
- Reworked Dashboard scan logic to use real folder structure for Checkpoint/LORA categorization
- Fixed incorrect category aggregation (models being grouped into wrong buckets)
- Added pie chart visualization with legend and percentage breakdown
- Added `All` selection behavior for dashboard content type scan

### v0.1.0
- Forge Neo-focused baseline
- Gradio 4 migration
- Smart auto-organization system with backup and rollback
- Extended architecture support (FLUX, Pony, Illustrious, Wan, Qwen, Z-Image, Lumina, etc.)

---

## 🗺️ Roadmap

### v0.5.0 — Dashboard as Console *(complete)*
- Export dashboard data to CSV / JSON
- Top models ranking per type (by folder count / size)
- Orphan folder detection (local files with no CivitAI match)

### v0.6.3 — Download Reliability Patch *(complete)*
- SHA256 integrity check after every download ✅
- Instant batch queueing (deferred API calls) ✅
- Thread-safe cancel via `threading.Event` ✅
- Aria2 auto-reconnect after RPC crash ✅
- Skipped model feedback in Download Manager ✅

### v0.6.2 — Queue Persistence + Restore Banner *(complete)*
- Server-side JSONL download log survives disconnects ✅
- Restore banner in Browser tab on reconnect ✅
- One-click re-queue through native download chain ✅

### v0.6.1 — Companion Banner + Download Fix *(complete)*
- Companion files banner for multi-file architectures ✅
- Wan 2.2 HN/LN role detection in banner ✅
- Web Worker fix for background-tab download stalling ✅

### v0.6.0 — Creator Management *(complete)*
- Favorite / ban creators directly in the UI ✅
- "Hide banned" toggle in browser listing ✅
- Saved search presets *(deferred to v0.7.0)*

### v0.7.0 — Advanced Curation *(planned)*
- Saved search presets
- ⭐ Favorites in User/creator search dropdown
- Additional browser quality-of-life improvements
- Batch enqueue API deferral (defer `update_model_versions` / `update_model_info` to download time, not enqueue time — speeds up large batch queuing significantly)
- `threading.Event` for cancel signals (replace busy-wait `while True / time.sleep(0.5)` in `download_cancel` / `download_cancel_all`)
- Aria2 auto-reconnect on retry (restart RPC if unreachable during status polling — improves resilience on RunPod/remote servers)

### v1.0.0 — First Stable Release *(planned)*
- All known regressions resolved
- Public documentation finalized
- Full Forge Neo compatibility guarantee

---

## 🎯 Features

> ⭐ = exclusive to Neo · everything else inherited and improved from the original fork

### 🔍 Browse & Search

- **Browse CivitAI** directly inside the WebUI — no browser switching needed
- **Search by keyword, tag, or username** — multiple search modes
- **Filter by content type**: Checkpoint, LORA, LoCon, DoRA, VAE, ControlNet, Upscaler, TextualInversion, Wildcards, Workflows, and more
- **Filter by base model**: SD 1.x, SDXL, Pony, Illustrious, FLUX, Wan, Qwen, Z-Image, NoobAI, Lumina, and many more — **auto-updated from CivitAI API** at startup (no hardcoded stale list) ⭐
- **Sort by**: Highest Rated, Most Downloaded, Newest, Most Liked, Most Discussed
- **Filter by time period**: Day, Week, Month, Year, All Time
- **NSFW toggle**: Show/hide NSFW content
- **Liked models only**: Filter to models you've liked on CivitAI (requires API key)
- **Hide installed models**: Declutter the browser by hiding already-downloaded models
- **Hide banned creators**: Client-side toggle that instantly hides cards from banned creators without a new search ⭐
- **Exact search**: Match search terms exactly instead of fuzzy
- **Search settings persist**: Sort, NSFW state, base model filter — all saved across restarts ⭐

### 📥 Download

- **Download any model, version, and file** directly from the browser
- **Aria2 high-speed multi-connection downloads** — optional, enabled by default
- **Download queue** — multiple downloads run in sequence without blocking the UI
- **Queue persistence** — the download queue is logged server-side; if the browser disconnects (e.g. RunPod timeout), a restore banner appears on reconnect so you can resume with one click ⭐
- **Cancel downloads** individually or all at once
- **Auto-set save folder** based on content type — no manual path typing needed
- **Custom sub-folders** — choose or create sub-folders per download
- **Custom save folder per type** — configure paths in Settings
- **Download URL override** — paste a direct URL to download a specific file
- **Proxy support** — SOCKS4/SOCKS5 for regions with restricted access
- **API key support** — download early access and private models with your CivitAI API key

### 🔄 Model Updates ⭐

- **Outdated card detection** — orange border on cards that have a newer version available
- **Batch update** — select multiple outdated models via checkbox and download all at once
- **Precise version comparison** — compares model family + version string (configurable)
- **Retention policy** — when updating, choose: `keep` both files, `move to _Trash`, or `replace` (permanent delete)
- **Audit log** — `neo_update_audit.jsonl` records every scan and retention action for traceability
- **Dashboard update summary** — after scanning, the Dashboard shows a live banner with outdated counts per type

### 🗂️ Auto-Organization ⭐

- **Organize new downloads automatically** into subfolders by base model type (SDXL/, Pony/, FLUX/, etc.)
- **Organize existing models** in one click from the Update Models tab
- **Validate organization** — read-only scan that checks every model against its `.json` metadata and reports ✅ correct / ❌ misplaced / ⚠️ no-metadata, with a per-file table ⭐
- **Fix misplaced files** — after validation, move only the flagged models to their correct subfolders in one click; backup created automatically ⭐
- **Backup before organizing** — automatic snapshot of current folder structure
- **One-click rollback** — restore previous structure at any time (keeps last 5 backups); also reverts fixes applied by the validator
- **Custom category patterns** — define your own base model → folder mapping in Settings (JSON)
- **Associated files moved together** — `.json`, `.png`, `.preview.png`, `.txt` files travel with the model

### 🖼️ Model Info & Preview

- **Model information panel** — shows name, version, base model, type, trained tags, permissions, description
- **Sample images** with a **"Send to txt2img"** button per image — fills prompt, negative, sampler, steps, CFG all at once
- **Individual meta field buttons** — click any field (Prompt, Negative, Seed, CFG...) to send just that value to txt2img. **Shift+click appends** to your existing prompt instead of replacing ⭐
- **Trained tags / trigger words** — displayed in the model info panel and in the **model overlay popup** (CivitAI icon on txt2img/img2img cards). The **"➕ Add to prompt" button** appends activation tags directly to your txt2img prompt and closes the overlay; for **LORA models it automatically prepends `<lora:filename:1>`** so the activation tag is always included ⭐
- **SHA256 in Version Information** — the model info overlay shows the SHA256 hash of the selected file; click once to select all for easy copy ⭐
- **Video preview** support — model cards with video samples play on hover (muted, loops automatically) ⭐
- **Image viewer** — click any preview image to open it fullscreen
- **Resize preview images** in cards — configurable max resolution (128–1024px) for faster loading
- **Save model info** — saves model data as `.json` and HTML with all sample images
- **Save images** — downloads all sample images locally
- **Use local HTML** — when clicking the CivitAI button on a model card in txt2img, open the locally saved HTML instead of fetching from the internet

### 📊 Dashboard & Statistics ⭐

- **Disk usage by category** — see exactly how much space each model type and architecture uses
- **File count per category** — know exactly what you have
- **Organized by base model** — Checkpoints and LORAs broken down by type (Pony, SDXL, FLUX, etc.)
- **Visual progress bars** and percentage breakdown
- **Pie chart** with legend
- **Hide empty categories** toggle for a cleaner view
- **Scan summary** — folders scanned, scan duration, skipped files, read errors
- **Update summary banner** — shows outdated model count per type after scanning

### 🃏 Model Cards

- **Color-coded borders**: green = installed, orange = update available, blue = early access, none = not installed
- **Color legend bar** — always-visible reference above the card grid ⭐
- **NSFW badge** on cards marked as adult content (configurable)
- **"Paid" badge** (💎) for early access models
- **Model type badge** on each card
- **Tile size** — configurable card size (smaller = more cards per row)
- **Sort by date** — group cards by upload date
- **Hide installed models** — remove already-downloaded models from the grid
- **Multi-select** — checkbox on outdated cards to select multiple for batch download ⭐
- **Quick delete** on installed/outdated cards — removes model directly from the card
- **👤 Creator Management** — ⭐ favorite or 🚫 ban a creator directly from the browser; favorited creator cards get a gold glow and ⭐ badge; banned creators can be hidden in one click ⭐

### 🔒 Safety & Integrity ⭐

- **Send deleted models to Trash** (OS recycle bin) instead of permanent delete — configurable in Settings (default: ON)
- **Filename length limit (246 bytes / UTF-8)** — prevents filesystem errors on Linux (ext4 max: 255 bytes), works correctly with multi-byte characters (Japanese, Chinese, etc.)
- **Illegal character sanitization** in filenames — removes characters forbidden by the OS automatically

### ⚙️ Settings

All settings are in **Forge Settings → CivitAI Browser Neo**:

| Setting | Default | Description |
|---------|---------|-------------|
| Personal API key | — | Required for some downloads and liked-only search |
| Hide early access models | OFF | Hides models behind a paywall |
| Individual prompt buttons | ON | Click each meta field to send it to txt2img |
| Shift+click meta fields | — | Appends to existing prompt instead of replacing |
| Move deleted to Trash | ON | OS recycle bin instead of permanent delete |
| Resize preview cards | ON | Resizes card thumbnails for faster loading |
| Resize preview size | 512px | Max width for card thumbnails |
| Video playback | ON | Card thumbnails play video on hover (muted). Disable if experiencing high CPU usage |
| Use local HTML | OFF | Open local HTML when clicking CivitAI button |
| Page navigation as header | OFF | Sticky top navigation bar |
| Auto-organize downloads | OFF | Organize new downloads by base model type |
| Retention policy | replace | What to do with old files on update |
| Debug prints | OFF | Verbose console output for troubleshooting |
| Use Aria2 | ON | High-speed multi-connection downloads |
| Proxy address | — | SOCKS4/SOCKS5 proxy for restricted regions |

---

## 📦 Installation

### For Forge Neo

1. Open Forge Neo WebUI
2. Navigate to **Extensions** → **Install from URL**
3. Paste: `https://github.com/eduardoabreu81/sd-civitai-browser-neo`
4. Click **Install** and reload WebUI

### Requirements

- ✅ [Stable Diffusion WebUI Forge - Neo](https://github.com/Haoming02/sd-webui-forge-classic/tree/neo)
- ✅ Python 3.10+ (3.13 recommended)
- ✅ Gradio 4.39.0+ (comes with Forge Neo)

> ⚠️ **Note**: This extension is designed for **Forge Neo only**. For Forge Classic or Automatic1111, I recommend the [anxety-solo fork of sd-civitai-browser-plus](https://github.com/anxety-solo/sd-civitai-browser-plus) — it is the most maintained non-Neo fork, based on the original [BlafKing version](https://github.com/BlafKing/sd-civitai-browser-plus).

---

## 📁 Auto-Organization System

### How It Works

The organization system analyzes your models based on their `baseModel` metadata (stored in `.json` files) and automatically organizes them into subfolders.

#### **Before Organization:**
```
models/Lora/
├── model1.safetensors (SDXL)
├── model2.safetensors (Pony)
├── model3.safetensors (FLUX)
├── random_folder/
│   └── model4.safetensors (SD1.5)
└── ...
```

#### **After Organization:**
```
models/Lora/
├── SDXL/
│   ├── model1.safetensors
│   ├── model1.json
│   └── model1.png
├── Pony/
│   └── model2.safetensors
├── FLUX/
│   └── model3.safetensors
├── SD/
│   └── model4.safetensors
└── ...
```

### Usage

#### **Option 1: Auto-Organize New Downloads**

1. Go to **Settings** → **Model Organization**
2. Enable **"Auto-organize downloads by model type"**
3. New downloads will automatically go to organized folders

#### **Option 2: Organize Existing Models**

1. Go to **CivitAI Browser Neo** tab
2. Go to **Update Models** sub-tab
3. Select model types (e.g., LORA)
4. Click **"📁 Organize models into subfolders by type"**
5. Wait for completion
6. (Optional) Click **"↶ Undo Last Organization"** if needed

### Safety Features

- ✅ **Automatic Backup**: Creates backup before any operation
- ✅ **One-Click Undo**: Restore original structure anytime
- ✅ **Associated Files**: Moves `.json`, `.png`, `.txt` files together
- ✅ **Conflict Detection**: Skips files that already exist at destination
- ✅ **Error Recovery**: Continues operation even if some files fail

---

## 📊 Dashboard & Statistics

### Overview

The Dashboard provides comprehensive insight into your model collection with detailed disk usage statistics organized by model type and architecture.

### Features

- **📈 Disk Usage Analysis**: See exactly how much space each model type uses
- **📁 Smart Categorization**: 
  - Checkpoints and LORAs organized by baseModel (Pony, SDXL, FLUX, Illustrious, etc.)
  - Other types shown as-is (VAE, ControlNet, Upscaler, etc.)
- **📊 Visual Breakdowns**: Progress bars showing percentage of total storage
- **🔍 Flexible Scanning**: Select which content types to analyze
- **⚡ Fast Detection**: Auto-detects organization from folder structure
- **🧹 Cleaner View**: Optional "Hide empty categories (0 files)" toggle
- **🧾 Scan Summary**: Displays folders scanned, duration, skipped files, and read errors

### Usage

1. Go to **CivitAI Browser Neo** → **Dashboard** tab
2. Select content types to analyze:
   - Check **"All"** to select everything
   - Or select individual types (Checkpoint, LORA, VAE, etc.)
3. Click **"📊 Generate Dashboard"**
4. View statistics with:
   - Total file count and size
  - Scan summary (folders scanned, scan duration, skipped files, read errors)
   - Breakdown by category
   - Percentage of total storage
   - Visual progress bars
5. Optional: Enable **"Hide empty categories (0 files)"** for a cleaner table/chart

### Example Output

```
2294 files (1.4 TB) → 12 categories

┌────────────────────────┬───────┬──────────────┬────────────┐
│ MODEL TYPE             │ FILES │ TOTAL SIZE   │ % OF TOTAL │
├────────────────────────┼───────┼──────────────┼────────────┤
│ Checkpoint → Other     │ 148   │ 968.3 GB     │ 70.0%      │
│ LORA → Other           │ 1960  │ 366.6 GB     │ 26.5%      │
│ LORA → SDXL            │ 59    │ 17.7 GB      │ 1.3%       │
│ Checkpoint → Illust... │ 2     │ 13.2 GB      │ 1.0%       │
│ LORA → SD              │ 66    │ 6.6 GB       │ 0.5%       │
│ LORA → Pony            │ 2     │ 386.7 MB     │ 0.0%       │
│ VAE                    │ 5     │ 1.2 GB       │ 0.1%       │
└────────────────────────┴───────┴──────────────┴────────────┘
```

### What It Shows

**For Checkpoints & LORAs:**
- Shows baseModel categorization (Pony, SDXL, FLUX, etc.)
- `→ Unorganized`: Files in root directory without organization
- `→ Other`: Files in "Other" subfolder or unrecognized types

**For Other Types:**
- VAE, ControlNet, TextualInversion: Shown as-is
- Upscalers: Grouped by type (ESRGAN, RealESRGAN, etc.)
- Detection, Wildcards, Workflows: Individual categories

### Smart Detection

The Dashboard intelligently detects organization:

1. **From folder structure**: Uses real subfolder layout for Checkpoint/LORA categories
2. **Root handling**: Files in the root Checkpoint/LORA folder are shown as `Unorganized`
3. **Direct scan**: Counts real files and sizes from disk (fast, no metadata dependency)

---

## 🎨 Supported Model Types

The Neo version includes detection for all modern architectures supported by Forge Neo:

| Category | Detection patterns | Notes |
|----------|-------------------|-------|
| **SD** | SD 1, SD1, SD 2, SD2 | Unified SD versions |
| **SDXL** | SDXL | Base SDXL |
| **Pony** | PONY | Pony V6 and variants |
| **Illustrious** | ILLUSTRIOUS | Illustrious XL |
| **NoobAI** | NOOBAI, NOOB AI, NAI | NoobAI (Illustrious variant) |
| **FLUX** | FLUX | Dev, Krea, Kontext, Klein |
| **Wan** | WAN | Wan 2.2 T2V/I2V |
| **Qwen** | QWEN | Qwen-Image, Edit |
| **Z-Image** | Z-IMAGE, ZIMAGE | Z-Image, Turbo |
| **Lumina** | LUMINA | Lumina-Image 2.0 |
| **Anima** | ANIMA | Anima |
| **Cascade** | CASCADE | Stable Cascade |
| **PixArt** | PIXART | PixArt |
| **Playground** | PLAYGROUND | Playground |
| **SVD** | SVD, STABLE VIDEO | Video Diffusion |
| **Hunyuan** | HUNYUAN | Hunyuan |
| **Kolors** | KOLORS | Kolors |
| **AuraFlow** | AURAFLOW | AuraFlow |
| **Chroma** | CHROMA | Chroma1-HD |
| **Other** | (unrecognized) | Configurable |

### Custom Categories

You can define your own categories in **Settings** → **Model Organization** using JSON format:

```json
{
  "SD": ["SD 1", "SD1", "SD 2", "SD2"],
  "SDXL": ["SDXL"],
  "MyCustomType": ["CUSTOM", "PATTERN"],
  "AnotherType": ["KEYWORD1", "KEYWORD2"]
}
```

---

## ⚠️ Known Issues

- Some models may not have `baseModel` metadata (download from CivitAI to get it)
- Dashboard shows "Unorganized" for files placed directly in root model folders
- Rollback only works for the last operation
- Maximum 5 backups are kept (older ones are deleted)

## 💡 Tips

- **First time using?** Update model info & tags to generate `.json` files with metadata
- **Want to see your collection?** Use Dashboard tab to analyze disk usage
- **Want custom folders?** Edit JSON in Settings → Model Organization
- **Made a mistake?** Use "Undo Organization" button immediately
- **Need help?** Check console logs (`[CivitAI Browser Neo]` prefix)

---

## 📄 Credits

### Original Project
- **[sd-civitai-browser](https://github.com/Vetchems/sd-civitai-browser)** by Vetchems
- **[sd-civitai-browser-plus](https://github.com/BlafKing/sd-civitai-browser-plus)** by BlafKing

### Feature Inspiration
- **[sd-webui-civbrowser](https://github.com/SignalFlagZ/sd-webui-civbrowser)** by SignalFlagZ — Creator Management pattern (UserInfo class, `.txt` storage, accordion UI, mutually exclusive lists)

### Anxety-Solo Fork
- **[sd-civitai-browser-plus](https://github.com/anxety-solo/sd-civitai-browser-plus)** by anxety-solo
  - Modern UI redesign
  - Quality of life improvements
  - Multiple bugfixes

### Neo Version
- **[sd-civitai-browser-neo](https://github.com/eduardoabreu81/sd-civitai-browser-neo)** by Eduardo Abreu
  - Forge Neo compatibility (Gradio 4.x)
  - Auto-organization system
  - Dashboard & statistics
  - Modern model support (FLUX, Pony, Wan, Qwen, etc)
  - Backup & rollback system

### Special Thanks
- **[Forge Neo](https://github.com/Haoming02/sd-webui-forge-classic/tree/neo)** by Haoming02
- All contributors to the original projects
- CivitAI for their amazing API

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Contributions are welcome! Feel free to:
- 🐛 Report bugs
- 💡 Suggest new features
- 🔧 Submit pull requests
- 📖 Improve documentation

---

## ☕ Support

If you find this extension helpful, consider:
- ⭐ Starring the repository
- 🐛 Reporting issues
- 📢 Sharing with others
- ☕ [Buy me a coffee](https://ko-fi.com/eduardoabreu81)

---

<div align="center">

Made with ❤️ for the Stable Diffusion community

**[Report Bug](https://github.com/eduardoabreu81/sd-civitai-browser-neo/issues)** • **[Request Feature](https://github.com/eduardoabreu81/sd-civitai-browser-neo/issues)** • **[Discussions](https://github.com/eduardoabreu81/sd-civitai-browser-neo/discussions)**

</div>
