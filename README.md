<div align="center">
  <img src=".github/logo.png?v=2" alt="CivitAI Browser Neo"/>
</div>

# 🎨 CivitAI Browser Neo

<div align="center">

[![Forge Neo](https://img.shields.io/badge/Forge-Neo-blue)](https://github.com/Haoming02/sd-webui-forge-classic/tree/neo)
[![Gradio](https://img.shields.io/badge/Gradio-4.40.0-orange)](https://gradio.app/)
[![Version](https://img.shields.io/badge/Version-1.0.0-brightgreen)](#-changelog)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Extension for [Stable Diffusion WebUI Forge - Neo](https://github.com/Haoming02/sd-webui-forge-classic/tree/neo)**

</div>

Browse, download, and manage your model library directly inside Forge Neo — multi-source discovery, a self-contained Local Models tab, LoRA categorization, auto-organization, disk usage dashboard, creator management, and support for all modern architectures (FLUX, Wan, Qwen, Krea 2, Pony, Illustrious, and more).

---

## 📋 Table of Contents

- [What's New](#-whats-new)
- [Changelog](#-changelog)
- [Roadmap](#️-roadmap)
- [Features](#-features)
- [Installation](#-installation)
- [Browser Sources](#-browser-sources)
- [Local Models & LoraDex](#-local-models--loradex)
- [Auto-Organization System](#-auto-organization-system)
- [Metadata Maintenance](#️-metadata-maintenance--recovery)
- [Paid vs. Early Access](#-paid-vs-early-access)
- [Native Extra Networks Cards](#-native-extra-networks-cards)
- [Dashboard & Statistics](#-dashboard--statistics)
- [Supported Model Types](#-supported-model-types)
- [Known Issues & Limitations](#️-known-issues--limitations)
- [Credits](#-credits)

---

## 🆕 What's New

### v1.0.0 — First Stable Release

The `revamp` line is now the released version. This is the largest update since the Neo fork: the Browser is no longer hardwired to CivitAI, the Local Models tab was rebuilt from scratch, and a LoRA categorization system ships alongside it.

- **Multi-Source Browser** — search through pluggable source adapters instead of CivitAI only: **CivArchive**, **ModelScope**, and **Arc en Ciel** join CivitAI in the source dropdown. See [Browser Sources](#-browser-sources).
- **Paste model URL** — paste a direct link from CivitAI, CivArchive, Hugging Face, ModelScope, or Arc en Ciel; the extension detects the provider, fetches the model, and renders a card ready for download. Hugging Face direct file links (including subfolders) resolve to the exact file.
- **Local Models rebuilt** — a self-contained tab with its own state, pagination (25/50/100), filters, and progress bar. **Update Models has been merged into it**, so scanning, batch updating, renaming, and deleting all live in one place. See [Local Models & LoraDex](#-local-models--loradex).
- **LoraDex** — a new sub-tab for managing LoRA categories: auto-suggestion from tags and description, manual override persisted to the `.json` sidecar, category badges on cards, and organization into `Lora/<base>/<category>/` subfolders.
- **Native Extra Networks cards** — the txt2img/img2img checkpoint and LoRA cards now carry base-model badges, LoRA category, trigger words, and the real CivitAI model name, read from local sidecars with no extra API calls. An opt-in theme restyles them to look like the CivitAI website. See [Native Extra Networks Cards](#-native-extra-networks-cards).
- **Paid and Early Access are told apart** — CivitAI's two paywalls no longer share a badge: a timed window that expires into a free download gets an aqua **Early Access** badge, a permanent Buzz purchase gets a gold **Paid** badge, each with its own hide filter. See [Paid vs. Early Access](#-paid-vs-early-access).
- **Metadata maintenance** — **Verify local metadata** checks that cached CivitAI IDs still resolve and that `.api_info.json` matches the file it sits next to; **Resolve via CivArchive** recovers real metadata for models that were delisted from CivitAI. See [Metadata Maintenance](#️-metadata-maintenance--recovery).
- **GGUF support** — `.gguf` is a first-class checkpoint format: scanned by Local Models, recognized as installed by Browser cards, with sidecars, delete actions, and update checks working the same as `.safetensors`/`.ckpt`.
- **Download and preview improvements** — previews can be saved as JPEG, Aria2 retries with backoff on HTTP 429, and freshly-published versions no longer show a false "Unable to load preview images" error.
- **Faster Local tab** — installed-version detection and bulk download no longer walk the model tree per card; a single indexed scan per batch replaced the per-card walk.
- **Account badge** — the Dashboard shows a passive CivitAI account status badge, auto-connected with your saved API key.

---

## 📖 Changelog

### v1.0.0 — First Stable Release

**Multi-Source Browser**
- Added a browser source adapter foundation (`scripts/browser_sources/`) with a Browser Source selector in the Browser tab.
- Added CivArchive, Hugging Face, Arc en Ciel, and ModelScope adapters.
- Added **URL search mode** (`browser_sources/url_parser.py`): detects the provider from a pasted link and populates the model panel. Hugging Face direct file links resolve the exact file, including subfolders, and fetch the real size from the resolve URL.
- Hugging Face is registered but hidden from the source dropdown — search results were too noisy, so discovery moved to URL-paste mode. Checkpoint search filtering prefers real model artifacts, separates LoRA from checkpoint results, and applies video pipeline filters for families such as Wan.
- Added the CivArchive-only **Deleted from CivitAI** filter, based on CivArchive's `is_deleted`/`deleted_at` data.
- Added external-source provenance: source badge, source URL, mirror/status notes, and download provenance in cards and detail panels.
- External-source file and image metadata is normalized to the legacy Browser shape so detail panels, downloads, sidecars, and preview saving stay compatible.

**Local Models**
- Rebuilt Local Models as a self-contained tab: own grid, state, base-model filter, progress bar, and Clear buttons, fully isolated from the Browser tab.
- Merged the Update Models tab into Local Models; bulk maintenance actions moved to the Organization tab.
- Added pagination (Per page 25/50/100 + Prev/Next + page slider) with server-side slicing of the cached list.
- Hybrid fetch: batched `/models` requests with per-id fallback when one model poisons a batch, chunked fetch and version-endpoint recovery for huge models, and automatic `civitai.com` → `civitai.red` fallback. Unresolvable models render as local-only cards instead of disappearing.
- Detail panel: trained tags with **Add to prompt**, **Download selected version**, a **File dropdown** for versions with multiple files (filename and SHA256 follow the selection), and a refresh when the version changes.
- Update flow: user-selectable versions, hybrid family/baseModel resolution, "only updates" as a pure client-side view filter, "Update to latest" without a prior scan, and a retention policy of keep / move to trash / replace (via `send2trash`).
- "Update to latest" keeps the installed baseModel family instead of jumping across families.
- Installed detection now also matches the cached `modelVersionId`, so renamed or hash-less files keep their green border; card buttons resolve the exact file by stem rather than prefix.
- Per-tab download progress bars and per-queue-item download origin, so a Local update no longer drives the Browser progress bar.

**LoRA categorization & LoraDex**
- Added the **LoraDex** sub-tab: paginated LoRA list with mini-thumbnails and zoom, per-item and batch Apply/Reset, filename column, and persistence to the `.json` sidecar as `loraCategory`.
- Added `categorize_lora_by_tags()` — auto-suggests a category from tags plus description, with filename and model name as extra hints. Categories are Character, Style, Clothing, Concept, Pose, Background, Utility, and Slider.
- Manual `loraCategory` always wins over auto-detection.
- Added a LoRA category badge below the model-type badge on cards.
- Modular organization: by base model, by LoRA category, or both (`civitai_neo_lora_category_sort`).
- `modelTags` falls back to the `.json` sidecar for LoraDex, organization, and update flows.

**Native Extra Networks cards**
- Added `build_native_card_badge_map()` — a local-sidecar-only pass (no API calls, no folder walk) that feeds base model, LoRA category, trigger words, and the real CivitAI name to WebUI's native Checkpoint and LoRA cards.
- Added the opt-in setting **CivitAI-style card theme (native Extra Networks cards)** (`civitai_native_card_theme`): type/base badges on top, name and action buttons on the bottom, hover-reveal actions.
- A `MutationObserver` re-applies badges to cards rendered after the initial load (tab switch, scroll).

**Paid vs. Early Access**
- Added `get_access_kind()` in `scripts/civitai_api.py` as the single classifier: a populated `paidAccess` object is itself the gate signal; `permanent` is evaluated before `endsAt`.
- Separate badges (aqua **Early Access** vs gold **Paid**), version-dropdown suffixes, detail-panel labels, and download messages.
- Split the old single setting into **Hide early access models** and **Hide paid models**.
- The download pre-flight guard blocks gated requests up front instead of letting CivitAI's silent redirect to the purchase page reach Aria2 as an `Unrecognized URI` error.
- `availability` is no longer used as a signal — the version endpoint returns it as `null` and the list endpoint returns `"Public"` for both gated kinds. Legacy `availability: 'EarlyAccess'` and `earlyAccessEndsAt` are still honored for older or mirrored payloads.

**Organization & metadata**
- Added **Verify local metadata** — detects `.api_info.json` corruption and modelIds that no longer resolve on CivitAI, with a guard that bails out with an explicit error when a global API failure would otherwise flag the entire library as delisted.
- Added **Resolve via CivArchive** — recovers real metadata for orphaned or corrupted local models from CivArchive.
- Fixed by-hash metadata lookups corrupting `.api_info.json` for unrelated files.
- Added a local review marker (`scripts/civitai_local_review.py`): **Mark for review** in the model detail panel and overlay, persisted to `config_states/local_review_status.json` keyed by SHA256.
- `.json` sidecars now persist the raw `baseModel` value alongside the legacy `sd version` field.
- Auto-organize recalculates defensively: a download about to land in a content-type root folder is redirected to the correct subfolder after fetching the model's `baseModel`.
- Custom organization categories can be defined in Settings with a JSON pattern list.

**Base models & formats**
- Added `.gguf` to model file detection, local scan, installed-file detection, organization, and sidecar resolution.
- Added Krea 2, LTXV, Ernie, Anima, Chroma, and Z-Image / Z-Image Turbo, with matching badges; the base-model list is restricted to what Forge Neo supports and kept sorted alphabetically.
- Hardened the version filter against a `None` `baseModel`.

**Download & preview**
- Preview images can be saved as JPEG (`preview_format`, `preview_jpeg_quality`); old `.preview.png`/`.png` duplicates are removed when switching format.
- Aria2 retries with backoff on HTTP 429.
- Fixed a false "Unable to load preview images" error on freshly-published versions: the extension retries through a second endpoint and, as a last resort, reuses the images already fetched for the model page — preserving per-image generation data instead of falling back to bare thumbnails.
- Fixed "Replace installed" regenerating the `.html`/`.json` sidecar with the *previous* version's data; the preview is now resolved against the version actually being downloaded.
- The Local Models detail panel rebuilds a cached preview that is stuck in the error state instead of serving the broken cache indefinitely.
- Gallery images are saved on Local-tab updates; `.json` and `.api_info.json` are refreshed when a model is updated.
- Batch download skips models that are already installed and up to date.

**Send to txt2img**
- Infotext is built from the card's own metadata, with an embedded-PNG fallback offered when a card image has no meta.
- SwarmUI embedded JSON is converted to A1111 infotext.
- A **Negative prompt** line is always emitted, so prompt-only cards still send correctly.
- The `#paste` click is deferred so Send-to-txt2img no longer clears the prompt it just filled.
- Stale Send-to-txt2img buttons in cached HTML sidecars are rewired.

**Account (MCP)**
- Added `scripts/civitai_mcp.py` and a passive account-status badge on the Dashboard, auto-connected with the saved API key. The badge hides itself on failure instead of showing an alarming error.

**Performance**
- Bulk download scans the model tree once per batch and respects the active base-model filter when picking the newest matching version.
- Installed-version detection reads from a known-files index instead of walking the tree per card.

**Refactors**
- Extracted HTML builders from `update_model_info` into `scripts/civitai_html_builder.py` (with tests).
- Browser filter defaults persist to an extension-local JSON file.

### v0.9.0 — CivitAI Domain Support, Update Mode Isolation & Download Resilience
- Added centralized domain helper (`get_civitai_domain()`) to replace all hardcoded `civitai.com` URLs across the extension.
- Added `civitai_sfw_only` checkbox setting (default: off → `civitai.red`) to toggle between domains.
- Fixed search-box direct-link parser to recognize both `civitai.com` and `civitai.red` URLs.
- Updated all API calls, model page links, uploader profile links, `Referer` headers, and JSON sidecar `modelPageURL` fields to use the configured domain.
- `initial_model_page`: verify `gl.update_mode` before resetting state; ignore Browser-tab filters when Update Mode is active.
- `download_create_thread`: on SHA256 mismatch, re-query `/api/v1/model-versions/{version_id}` to detect silent file updates by the author.
- `create_model_item` / `selected_to_queue`: propagate `version_id` through the download queue for post-download API recheck.
- `resolve_ambiguity`: defensively sync `model_sha256` and `model_filename` with the chosen candidate.
- Hardened `initial_model_page` and `update_model_info` against malformed `gl.json_data` (e.g. SHA256 ambiguity dicts without `items`/`metadata`).
- Exact search restricted to Model name only — CivitAI API does not support quoted search for Tag or User name.
- Batch download internal loop eliminates Gradio event-queue gaps between items.
- Timeout increased to 30s with automatic retry (up to 3×) for network failures.
- SHA256 verification buffer increased from 1MB to 8MB.
- Update list sorted by file modification time (most recent first).
- Fix re-trigger loop on `queue_trigger` preventing duplicate download executions.

### v0.8.3 — Safer Delete Flow for Installed/Outdated Models
- Browser version dropdown now defaults to an installed version whenever one exists, even when updates are available.
- This preserves delete action availability for models that are installed but outdated.
- Added a delete failsafe for card quick delete: if multiple installed versions exist, quick delete is canceled and the user is instructed to pick the exact installed version in the Browser panel before deleting.
- Installed-model Browser loading now keeps unmatched files visible as local-only entries while still using API data for matched models.

### v0.8.2 — Checkpoint SHA256 Cache Sync
- Added automatic SHA256 cache sync for checkpoints right after successful download completion.
- Added a manual `Sync checkpoint SHA256 cache` button in Update Models to reconcile local checkpoints against Forge cache.
- Added local checkpoint hash registry (`lib/models/checkpoint_hashes.json`) to track synced entries and clean stale records for deleted files.

### v0.8.1 — Trigger Word Bugfixes & Resilience
- Fixed an issue where the local trigger word fallback process ignored API groups and flattened words into single lines.
- Fixed an issue where "Update model info & tags" didn't safely persist incoming `trainedWords` groups natively to the local cache.
- Added exponential backoff retry mechanism to API calls returning temporary 50x server errors, saving "Update models" loops from failing silently on affected files.
- Moved trigger word row buttons (📋 / ➕) to the left side of the text in the preview panel.

### v0.8.0 — Trigger Word Consolidation
- Consolidated trigger words from `.safetensors` metadata, local `.json` `activation text`, and API `trainedWords`
- Added case-insensitive deduplication while preserving original order
- Model info now uses local consolidated trigger words first, with API fallback when local cache is unavailable

### v0.7.4 — Wan I2V/T2V Differentiation
- Wan card badges now distinguish `I2V`, `T2V`, and `TI2V` subtypes (API already returns specific `baseModel` values)
- New setting `civitai_neo_wan_subfolder_by_type` (OFF by default): splits Wan downloads into `Wan/I2V/`, `Wan/T2V/`, `Wan/TI2V/` subfolders
- Fixed multi-level subfolder "already organized" check (was using `os.path.basename`, broke for `Wan/I2V` paths)
- Fixed Flux.2 Klein 4B/9B and Flux.2 D showing `F1` badge — now correctly shows `F2`

### v0.7.3 — Per-group Trigger Word Rows
- Each trigger word group gets its own row with individual copy and add-to-prompt buttons
- LORA tag row (`<lora:filename:1>`) shown as first entry in purple/monospace
- Clipboard copy with ✓ visual feedback (1.5s)
- "Add all to prompt" button when multiple groups exist

### v0.7.2 — Bug Fixes
- Fixed wildcard base-model subfolder being applied in GUI even when `wildcard_organize_by_base` is OFF (`civitai_api.py` path calculation was missing the wildcard guard)
- Fixed delete-by-SHA256 silently failing — `json_base` path not joined with `root`, making `os.path.exists` search in CWD instead of the model directory

### v0.7.1 — Wildcard Download Improvements
- Own subfolder per wildcard download (sd-dynamic-prompts compatible)
- Flat zip extraction — no double-nesting when the zip has internal folders
- Skip preview/gallery images for Wildcards
- New settings: `wildcard_own_folder` (ON by default), `wildcard_organize_by_base` (OFF by default)

### v0.6.3 — Download Reliability
- **File integrity check** — every download is verified against CivitAI's expected hash after completing; corrupted or incomplete files are detected and removed automatically
- **Faster batch queueing** — adding many models to the queue is now instant; metadata is fetched only when each download actually starts, not at queue time
- **Safer cancel** — cancelling a download or clearing the queue is now more reliable and won't cause hangs
- **Aria2 auto-reconnect** — if the download engine crashes during a session, it automatically restarts and resumes the current download
- **Skipped model feedback** — if a model can't be queued during batch selection, a visible error message appears in the Download Manager

### v0.6.2 — Queue Persistence
- **Download queue survives disconnects** — the queue is saved server-side; if your session ends (e.g. RunPod timeout), a restore banner appears next time you open the UI
- **One-click restore** — re-queue all interrupted downloads with a single button click

### v0.6.1 — Companion Files Banner
- **Companion files guidance** — a warning banner appears when downloading models that require additional files (e.g. Wan 2.2, FLUX, Qwen), with specific instructions per architecture
- **Background download fix** — downloads no longer stall when the browser tab is in the background

### v0.6.0 — Creator Management
- **Favorite creators** — mark creators as favorites; their cards get a gold glow and ⭐ badge
- **Ban creators** — hide cards from creators you don't want to see; one-click toggle
- **Persistent lists** — favorites and bans are saved to disk and restored across sessions
- **Mutually exclusive** — favoriting a creator removes them from the ban list and vice versa

### v0.5.0 — Dashboard Export & Rankings
- **Export dashboard** — download your collection stats as CSV or JSON
- **Top 10 largest files** — see which individual models take the most space
- **Top 10 categories by file count**
- **Orphan detection** — optional scan to find model files with missing or incomplete metadata

### v0.4.5 — Removed Model Handling
- **Graceful 404 handling** — when a model has been deleted from CivitAI, the extension shows the locally cached info instead of an error, with a clear warning banner

### v0.4.4 — Model Info Polish
- **LoRA activation syntax** — "Add to prompt" now inserts the correct `<lora:filename:1>` syntax automatically
- **SHA256 in model info** — hash shown in the version details; click to select for easy copy
- **Live progress bars** — Validate and Fix operations now show real-time progress

### v0.4.3 — Organization Validator
- **Validate organization** — read-only scan that shows which models are correctly placed, misplaced, or missing metadata
- **Fix misplaced files** — move flagged models to the correct folders in one click; backup created automatically
- **Instant undo** — revert the fix immediately without scrolling to the Undo section

### v0.4.2
- "Add to prompt" button now works in the model info overlay (CivitAI icon in txt2img/img2img)
- Various crash fixes

### v0.4.1
- Shift+click on meta field buttons to append to prompt instead of replacing
- Deleted models go to the OS recycle bin by default
- Search settings now persist correctly across restarts

### v0.4.0 — Update Intelligence
- Dashboard banner showing outdated model counts after scanning
- Batch update — select multiple outdated models and download all at once
- Version comparison by model family (not just version name)
- Retention policy on update: keep, move to trash, or replace

### v0.3.x
- Card color legend bar above the browser grid
- DNS retry on transient network failures
- Dashboard UX improvements (hide empty categories, scan summary)

### v0.1.0 — Neo Baseline
- Full Forge Neo / Gradio 4 compatibility
- Auto-organization system with backup and rollback
- Extended architecture support

---

## 🗺️ Roadmap

### v0.7.0 — Forge Neo Compatibility *(complete)* ✅

### v0.7.1 — Wildcard Download Improvements *(complete)* ✅

### v0.7.2 — Bug Fixes *(complete)* ✅

### v0.7.3 — Per-group Trigger Word Rows *(complete)* ✅

### v0.7.4 — Wan I2V/T2V Differentiation *(complete)* ✅

### v0.8.0 — Trigger Word Consolidation *(complete)* ✅

### v0.8.1 — Trigger Word Bugfixes & Resilience *(complete)* ✅

### v0.8.2 — Checkpoint SHA256 Cache Sync *(complete)* ✅

### v0.8.3 — Safer Delete Flow for Installed/Outdated Models *(complete)* ✅

### v0.9.0 — CivitAI Domain Support, Update Mode Isolation & Download Resilience *(complete)* ✅

### v1.0.0 — First Stable Release *(complete)* ✅
- Multi-Source Browser: direct adapters for CivitAI, CivArchive, ModelScope, and Arc en Ciel, plus paste-a-URL support for Hugging Face
- **Deleted from CivitAI** filter for CivArchive
- External-source provenance in cards and detail panels
- Local Models rebuilt: self-contained, paginated, with Update Models merged in
- LoraDex and LoRA category management
- Native Extra Networks card badges and the opt-in CivitAI-style card theme
- Paid vs. Early Access separation with independent hide filters
- Metadata verification and CivArchive recovery for delisted models
- Explicit GGUF support across download, organization, local review, and metadata flows
- Passive account badge on the Dashboard

### v1.1.0 — Curation Depth *(planned)*
- **Cross-source SHA256 double-check** against CivitAI metadata when external sources provide or allow resolving a file hash
- **Not found on CivitAI** filter, as a state distinct from "Deleted from CivitAI"
- **Hugging Face curated catalog** for safer discovery of Forge-compatible repositories (until then, HF stays URL-only)
- **Organization by Tag — Phase 1**: save CivitAI tags to the `.json` sidecar; editable user-tags field in the model panel
- **Organization by Tag — Phase 2**: pick "anchor" tags in the Organization tab → models with that tag sort into `<type>/<tag>/` subfolders, independent of base-model organization
- Saved search presets
- Favorites in creator/user search
- Additional direct adapters (TensorArt, SeaArt, PixAI, Shakker, Tungsten, Civision, TensorHub, Yodayo, Moescape)

---

## 🎯 Features

> ⭐ = exclusive to Neo

### 🔍 Browse & Search

- Browse CivitAI directly inside the WebUI — no tab switching
- Select a Browser source adapter: CivitAI, CivArchive, ModelScope, or Arc en Ciel ⭐
- Search by model name, tag, username, or **paste a direct model URL** ⭐
- Filter by content type: Checkpoint, LORA, VAE, ControlNet, Upscaler, TextualInversion, Wildcards, Workflows, and more
- Filter by base model: SD 1.x, SDXL, Pony, Illustrious, FLUX, Krea 2, Wan, Qwen, NoobAI, Lumina, LTXV, Ernie, Anima, Chroma, Z-Image, and more — list auto-updated from CivitAI at startup ⭐
- Sort by: Highest Rated, Most Downloaded, Newest, Most Liked, Most Discussed
- Filter by time period: Day, Week, Month, Year, All Time
- NSFW toggle, liked-only filter, hide installed models, hide banned creators
- Independent **Hide early access** and **Hide paid** filters ⭐
- Exact search mode
- Search settings persist across restarts ⭐

### 📥 Download

- Download any model, version, and file variant directly (`.safetensors`, `.ckpt`, `.gguf`, etc.)
- High-speed multi-connection downloads via Aria2 (optional, on by default)
- Download queue — multiple downloads run in sequence without blocking the UI
- Queue persistence — survives session disconnects with one-click restore ⭐
- Independent progress bars for the Browser and Local Models tabs ⭐
- Cancel individually or clear the entire queue
- Folder automatically set based on content type ⭐
- Custom sub-folders per download
- File integrity check with silent-update detection — a hash mismatch re-queries the API before failing ⭐
- Aria2 retry with backoff on HTTP 429 ⭐
- API key support for early access, paid, and private models
- Proxy support for restricted regions

### 🏠 Local Models ⭐

- Self-contained tab for the models installed on your machine — browse, rename, update, and delete
- Update Models merged in: outdated models get an orange border and can be updated in batch
- Pagination: 25 / 50 / 100 cards per page, with Prev/Next and a page slider
- Sort by name or download date; filter by content type and base model
- "Only models with updates" as an instant client-side view filter
- Retention policy on update: keep alongside, move to trash, or replace
- Detail panel with version dropdown, **File dropdown** for multi-file versions, trained tags with "Add to prompt", and "Download selected version"
- Resilient metadata fetch: batched requests with per-id fallback, version-endpoint recovery, and `civitai.com` → `civitai.red` fallback — models the API can't resolve still show as local-only cards

### 🏷️ LoRA Categorization & LoraDex ⭐

- **LoraDex** sub-tab: paginated LoRA list with mini-thumbnails and zoom
- Auto-suggested categories from tags, description, filename, and model name
- Manual category assignment per LoRA, applied individually or in batch, persisted to the `.json` sidecar
- Category badge on model cards
- Organize LoRAs into `Lora/<base>/<category>/` subfolders — on download and in bulk

### 🔄 Model Updates ⭐

- Orange border on cards with a newer version available
- Batch update — select multiple outdated models and download all at once
- User-selectable target version, resolved by model family rather than version name alone
- "Update to latest" keeps the installed base-model family
- Dashboard shows outdated model counts after scanning

### 🗂️ Auto-Organization ⭐

- New downloads automatically sorted into subfolders by base model (SDXL/, Pony/, FLUX/, etc.)
- Modular: organize by base model, by LoRA category, or both
- Organize your existing collection in one click
- Validate organization — read-only check showing correct / misplaced / no-metadata per file ⭐
- Fix misplaced files in one click — automatic backup created first ⭐
- One-click rollback (keeps last 5 backups)
- Custom folder mapping in Settings
- Associated files (`.json`, `.png`, `.txt`) always move with the model

### 🗄️ Metadata Maintenance ⭐

- **Verify local metadata** — check that cached CivitAI IDs still resolve and that `.api_info.json` matches the file it sits beside
- **Resolve via CivArchive** — recover real metadata for models delisted from CivitAI
- **Mark for review** — flag a local model for later attention; status is stored by SHA256
- Bulk metadata, tag, and preview refresh from CivitAI

### 🖼️ Model Info & Preview

- Model info panel with name, version, base model, type, tags, permissions, and description
- Sample images with "Send to txt2img" — fills prompt, negative, sampler, steps, CFG
- Individual meta field buttons — send just one field; Shift+click to append ⭐
- "➕ Add to prompt" in the model overlay — appends trigger words directly; auto-inserts LoRA syntax ⭐
- SHA256 hash shown in version info — click to select ⭐
- Video preview on hover for cards with video samples ⭐
- Save model info and images locally, as PNG or JPEG ⭐

### 📊 Dashboard ⭐

- Disk usage by category and architecture
- Pie chart with percentage breakdown
- Top 10 largest files and categories
- Orphan file detection (optional)
- Export to CSV or JSON
- Update summary after scanning
- Passive CivitAI account status badge

### 🃏 Model Cards

- Color-coded borders: aquamarine = installed, orange = outdated, gold = favorite creator
- Color legend bar always visible above the grid ⭐
- NSFW, access, type, base-model, and LoRA-category badges ⭐
- Paid models are told apart from early access ⭐ — see [Paid vs. Early Access](#-paid-vs-early-access)
- Configurable tile size
- Quick delete from the card
- Multi-select checkboxes for batch download ⭐
- Favorite (⭐) and ban (🚫) creator directly from the card ⭐
- Optional CivitAI-style theme for WebUI's own Extra Networks cards ⭐

### 🔒 Safety

- Deleted models go to the OS recycle bin by default (configurable)
- Filename sanitization — removes illegal characters automatically
- Filename length capped to prevent filesystem errors
- Automatic backup before organize/fix operations (keeps last 5)
- Conflict detection — existing files at the destination are skipped

---

## 📦 Installation

1. Open Forge Neo WebUI
2. Go to **Extensions** → **Install from URL**
3. Paste: `https://github.com/eduardoabreu81/sd-civitai-browser-neo`
4. Click **Install** and reload the WebUI

> ⚠️ This extension requires **Forge Neo**. For Forge Classic or Automatic1111, use the [anxety-solo fork](https://github.com/anxety-solo/sd-civitai-browser-plus).

---

## 🌐 Browser Sources

The Browser tab routes searches through pluggable source adapters. CivitAI remains the source of truth for metadata and SHA256 validation; the other sources are additive.

| Source | Current role | Notes |
|---|---|---|
| **CivitAI** | Primary catalog and metadata source | Full native support: API key, SHA256 validation, previews, permissions, and update checks. |
| **CivArchive** | Backup/mirror of CivitAI records | Supports the source-specific **Deleted from CivitAI** filter. Pagination is client-side over the public search window CivArchive returns. |
| **ModelScope** | Direct search/browse adapter | Searches modelscope.cn; content type and base model are detected from tags/metadata and normalized to Browser cards. |
| **Arc en Ciel** | External-source adapter | Search, pagination, detail panel, and download validated in Forge Neo. |
| **Hugging Face** | Direct URL download only | Browsing HF search results proved too noisy, so discovery moved to URL-paste mode. The adapter stays registered but is hidden from the dropdown. |

### Paste model URL

Switch the Browser search mode to **URL** and paste any supported link:

- `civitai.com/models/...` or `civitai.red/models/...`
- `civitai.com/api/...`
- `civarchive.com/...`
- `huggingface.co/<owner>/<repo>` (repo root)
- `huggingface.co/<owner>/<repo>/blob/main/<sub/folder/file.safetensors>` (direct file link, including subfolders)
- `modelscope.cn/models/...`
- `arcenciel.io/models/...`

The extension detects the provider, fetches the model, renders a single card, and populates the model panel for download. For Hugging Face file links the exact file is selected as the primary download and its real size is fetched from the resolve URL.

### Source-specific behavior

- **Deleted from CivitAI** only applies to CivArchive. It means CivArchive marks the model as removed from CivitAI; it does not mean "exclusive to another platform".
- **Not found on CivitAI** is planned separately and requires a cross-source SHA256 double-check — it must not be conflated with deleted records.
- Non-CivitAI cards and detail panels show the origin source, source URL, mirror/status notes, and download provenance.
- External-source file and image metadata is normalized to the same shape CivitAI uses, so size, format, and preview handling stay compatible.
- Future adapters should prefer official/public APIs over page scraping.

---

## 🏠 Local Models & LoraDex

The **Local Models** tab is where your installed library lives. It has its own state, filters, pagination, and download progress bar, fully independent from the Browser tab.

### Local Models Browser

1. Pick the content types and (optionally) base models you want to see
2. Click **📋 Load local models**
3. Cards render with installed/outdated borders; click one to open the detail panel

From the detail panel you can rename, delete, pick a version and file, add trigger words to the prompt, download a specific version, or update to the latest.

For batch work: tick the checkboxes on outdated cards, choose **When updating:** *Replace installed* or *Keep installed (download alongside)*, then click **⬆️ Update selected**. The **⬆️ Only models with updates** checkbox filters the current view instantly, without re-scanning.

Models the CivitAI API cannot resolve — delisted, renamed, or hash-less — still appear as local-only cards, so nothing disappears from your library view.

### LoraDex

The **LoraDex** sub-tab manages LoRA categories:

- Every LoRA gets a suggested category derived from its tags, description, filename, and model name
- Override it manually per row, or apply/reset pending changes in bulk
- The choice is saved to the `.json` sidecar as `loraCategory` and always wins over auto-detection
- Categories are Character, Style, Clothing, Concept, Pose, Background, Utility, and Slider

With **Organize LoRAs by category** enabled, new downloads and bulk organization sort LoRAs into `Lora/<base>/<category>/` — either combined with base-model organization or on its own.

---

## 📁 Auto-Organization System

The organization system sorts your models into subfolders based on their base model type, using the metadata saved alongside each file.

**Before:**
```
models/Lora/
├── model1.safetensors  (SDXL)
├── model2.safetensors  (Pony)
└── model3.safetensors  (FLUX)
```

**After:**
```
models/Lora/
├── SDXL/model1.safetensors
├── Pony/model2.safetensors
└── FLUX/model3.safetensors
```

### Auto-organize new downloads
Enable **"Auto-organize downloads"** in Settings → Model Organization.

### Organize existing models
Go to the **Organization** tab → pick the content types → choose the **Organization mode** (by base model, by LoRA category, or both) → click **📁 Organize into subfolders**.

### Safety
- Automatic backup before any operation (keeps the last 5)
- One-click undo
- Conflict detection (skips files that already exist at destination)
- Associated files (`.json`, `.png`, `.txt`) always move with the model

---

## 🗄️ Metadata Maintenance & Recovery

Sidecar metadata drifts: models get delisted from CivitAI, a by-hash lookup writes the wrong record, or a file is renamed until nothing matches it any more. The **Organization** tab has two tools for that.

### Verify local metadata

**🔍 Verify local metadata** checks every scanned model and reports two kinds of problem:

- **Removed from CivitAI** — the `modelId` cached in the `.json` sidecar no longer resolves on CivitAI
- **Mismatched metadata** — the `.api_info.json` next to the file describes a different model

Transient API failures are not counted as delisting: if the API is globally unreachable, the scan stops with an explicit error instead of flagging your entire library as removed.

### Resolve via CivArchive

When the verification finds problems, **🗄️ Resolve via CivArchive** appears. It queries CivArchive — a mirror that keeps records of models removed from CivitAI — and restores real metadata for the affected files, so delisted models keep working names, versions, and previews instead of decaying into unidentifiable files.

### Mark for review

The model detail panel and the model overlay have a **Mark for review** button for anything you want to revisit — a suspect duplicate, a file you may want to delete, a model whose metadata looks wrong. The status is stored in `config_states/local_review_status.json`, keyed by SHA256, so it survives renames and re-organization.

---

## 💎 Paid vs. Early Access

CivitAI runs **two different paywalls**, and the difference matters: one expires on its
own, the other never does. The browser labels them separately so you can tell at a glance
whether a model is worth waiting for.

| Badge | What it means | Does it become free? |
|---|---|---|
| 🟦 **Early Access** (aqua) | The creator opened a timed early-access window. Buzz unlocks it right now. | **Yes** — automatically, once the window closes. The detail panel shows the exact date: *"Early Access (free after 2026-08-10)"*. |
| 🟨 **Paid** (gold) | A permanent purchase with yellow Buzz. | **No** — never. The detail panel shows *"Paid (Buzz purchase)"*. |

Both badges appear on the model card next to the type badge, and both are repeated as a
suffix in the version dropdown — `v1.0 (Early Access)` vs `v1.0 (Paid)` — because a single
model can mix free, early-access and paid versions.

**How the two are told apart.** A populated `paidAccess` object is itself the gate signal;
its fields only say *which* gate applies:

| API shape | Reported as |
|---|---|
| `paidAccess: {permanent: false, endsAt: <future date>}` | Early Access |
| `paidAccess: {permanent: true, endsAt: null}` | Paid |
| `paidAccess: {permanent: false, endsAt: null}` | Paid |

The third shape is rare but real. It is reported as **Paid**, not Early Access, because
with no published date there is nothing to wait for and an "it becomes free later" label
would be a lie. An `endsAt` in the **past** means the window already closed — the version
is genuinely free again. `permanent` is evaluated before `endsAt`, so a stale end date
cannot downgrade a permanent purchase.

**Downloads are blocked before they start.** CivitAI answers a download request for a
gated version with a silent redirect to its purchase page, which used to surface as a
confusing Aria2 error. The browser now detects the gate up front and explains which one
applies, so you know whether waiting is an option.

**Hiding them.** Two independent settings under **Settings → CivitAI Browser Neo**:

- **Hide early access models** — hides only the timed kind
- **Hide paid models** — hides only the permanent kind

> ⚠️ These were a single setting before. If you previously used *"Hide early access models"*
> to keep all paid content out of the grid, enable **both** — the old setting no longer
> covers permanently-paid versions.

An API key (**Settings → CivitAI Browser Neo → API key**) is still required to download
any gated model you have already purchased.

---

## 🎴 Native Extra Networks Cards

The extension can enrich WebUI's **own** checkpoint and LoRA cards in txt2img/img2img — the ones under Extra Networks — using the sidecars already on disk. No extra API calls, no folder walk, so it is safe to run on every Extra Networks refresh.

Each native card can show:

- The base model badge (IL, Pony, FLUX, SDXL, …)
- The confirmed LoRA category
- Trigger words
- The real CivitAI model name instead of the filename

Cards rendered after the initial page load — when you switch tabs or scroll — pick up their badges automatically through a `MutationObserver`.

### CivitAI-style card theme

**Settings → CivitAI Browser Neo → CivitAI-style card theme (native Extra Networks cards)** (off by default) restyles those cards to look like the CivitAI website: type and base-model badges on top, name plus action buttons on the bottom, actions revealed on hover. It is purely visual (CSS) and safe alongside other UI themes.

---

## 📊 Dashboard & Statistics

Go to the **Dashboard** tab, select the content types you want to analyze, and click **"📊 Generate Dashboard"**.

You'll see:
- Total file count and disk usage
- Breakdown by category and architecture (Checkpoints and LORAs split by Pony, SDXL, FLUX, etc.)
- Visual progress bars and pie chart
- Top 10 largest files and categories
- Optional orphan file detection

Results can be exported as CSV or JSON.

The Dashboard also shows a passive **account status badge**: it auto-connects with your saved API key and displays the connected CivitAI username. No actions are tied to it — if the connection fails, the badge simply hides itself.

---

## 🎨 Supported Model Types

| Architecture | Notes |
|---|---|
| SD 1.x / SD 2.x | Classic Stable Diffusion |
| SDXL | Base SDXL and derivatives |
| Pony | Pony V6 and variants |
| Illustrious | Illustrious XL |
| NoobAI | NoobAI (Illustrious-based) |
| FLUX | Dev, Krea, Kontext, Klein |
| Krea 2 | Krea 2 turbo and related variants |
| Wan | Wan 2.2 — text/image to video |
| Qwen | Qwen-Image, Qwen-Image-Edit |
| Z-Image | Z-Image, Z-Image Turbo |
| LTXV | LTXV video/image model family |
| Lumina | Lumina-Image 2.0 |
| Anima | Anima |
| Chroma | Chroma1-HD |
| Ernie | Ernie-Image / Ernie-Image-Turbo |
| Cascade | Stable Cascade |
| SVD | Stable Video Diffusion |
| Hunyuan | Hunyuan |
| Other | Catch-all; fully configurable |

**File formats:** `.safetensors`, `.ckpt`, `.gguf`, `.pt`, `.pth`, `.bin`, `.th`, `.vae`, and `.zip` (Wildcards).

> **Krea 2 note:** the `krea2_turbo_fp8_scaled.safetensors` checkpoint requires the Qwen-Image VAE (`qwen_image_vae.safetensors`) and the Qwen3VL 4B text encoder (`qwen3vl_4b_fp8_scaled.safetensors`) rather than FLUX text encoders. Place both files in the Forge Neo `models/text_encoder/` folder.

Custom categories can be defined in **Settings → Model Organization** using a simple JSON pattern list.

---

## ⚠️ Known Issues & Limitations

- Update detection still depends partly on filename and model-name matching, and may miss some outdated models.
- `nsfwLevel` checks are not 100% accurate.
- ModelScope content-type and base-model detection is heuristic and may misclassify unusual models.
- Cross-source SHA256 double-check and a separate **Not found on CivitAI** filter are not implemented yet (planned for v1.1.0).
- Hugging Face remains URL-only until a curated catalog is built.
- CivArchive pagination is client-side over the public search window that CivArchive returns.

---

## 📄 Credits

- **[sd-civitai-browser](https://github.com/Vetchems/sd-civitai-browser)** by Vetchems — original project
- **[sd-civitai-browser-plus](https://github.com/BlafKing/sd-civitai-browser-plus)** by BlafKing — foundation for this fork
- **[sd-civitai-browser-plus](https://github.com/anxety-solo/sd-civitai-browser-plus)** by anxety-solo — UI redesign and quality improvements
- **[sd-webui-civbrowser](https://github.com/SignalFlagZ/sd-webui-civbrowser)** by SignalFlagZ — creator management inspiration
- **[CivArchive](https://civarchive.com)** — mirror used to recover metadata for delisted models
- **[Forge Neo](https://github.com/Haoming02/sd-webui-forge-classic/tree/neo)** by Haoming02

---

## 📜 License

MIT — see [LICENSE](LICENSE)

---

<div align="center">

Made with ❤️ for the Stable Diffusion community

**[Report Bug](https://github.com/eduardoabreu81/sd-civitai-browser-neo/issues)** • **[Request Feature](https://github.com/eduardoabreu81/sd-civitai-browser-neo/issues)** • **[Discussions](https://github.com/eduardoabreu81/sd-civitai-browser-neo/discussions)** • **[☕ Ko-fi](https://ko-fi.com/eduardoabreu81)**

</div>
