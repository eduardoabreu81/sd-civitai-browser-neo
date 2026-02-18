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
- [What's New](#-whats-new--v041)
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

---

## 🆕 What's New — v0.4.1

> **UX Polish** — better prompt integration, safer file handling, complete documentation.

- **Trigger words button** — "➕ Add to prompt" button next to the Trained Tags field sends activation tags directly to the txt2img prompt
- **Shift+click to append** — on individual meta field buttons (Prompt, Negative), Shift+click appends to your existing prompt instead of replacing it. Tooltip visible on hover.
- **Send to Trash setting** — new setting to move deleted models to the OS recycle bin instead of permanent deletion (default: ON)
- **Filename length safety** — filenames are now capped at 246 bytes (UTF-8) to prevent filesystem crashes on Linux
- **Search settings persist** — sort, NSFW state, base model filter and other preferences are now correctly saved and restored after restart
- **Full feature documentation** — README completely rewritten to document every feature, including hidden/undocumented ones from previous forks

---

## 📖 SD Civitai Browser Neo Release Story

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

### v0.5.0 — Dashboard as Console *(planned)*
- Export dashboard data to CSV / JSON
- Top models ranking per type (by folder count / size)
- Orphan folder detection (local files with no CivitAI match)

### v0.6.0 — Advanced Curation *(planned)*
- Favorite / ban creators directly in the UI
- Saved search presets
- "Hide banned" toggle in browser listing

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
- **Filter by base model**: SD 1.x, SDXL, Pony, Illustrious, FLUX, Wan, Qwen, Z-Image, NoobAI, Lumina, and many more — **auto-updated from CivitAI API** at startup (no hardcoded stale list)
- **Sort by**: Highest Rated, Most Downloaded, Newest, Most Liked, Most Discussed
- **Filter by time period**: Day, Week, Month, Year, All Time
- **NSFW toggle**: Show/hide NSFW content
- **Liked models only**: Filter to models you've liked on CivitAI (requires API key)
- **Hide installed models**: Declutter the browser by hiding already-downloaded models
- **Exact search**: Match search terms exactly instead of fuzzy
- **Search settings persist**: Sort, NSFW state, base model filter — all saved across restarts

### 📥 Download

- **Download any model, version, and file** directly from the browser
- **Aria2 high-speed multi-connection downloads** — optional, enabled by default
- **Download queue** — multiple downloads run in sequence without blocking the UI
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
- **Backup before organizing** — automatic snapshot of current folder structure
- **One-click rollback** — restore previous structure at any time (keeps last 5 backups)
- **Custom category patterns** — define your own base model → folder mapping in Settings (JSON)
- **Associated files moved together** — `.json`, `.png`, `.preview.png`, `.txt` files travel with the model

### 🖼️ Model Info & Preview

- **Model information panel** — shows name, version, base model, type, trained tags, permissions, description
- **Sample images** with a **"Send to txt2img"** button per image — fills prompt, negative, sampler, steps, CFG all at once
- **Individual meta field buttons** — click any field (Prompt, Negative, Seed, CFG...) to send just that value to txt2img. **Shift+click appends** to your existing prompt instead of replacing
- **Trained tags / trigger words** displayed in a dedicated field with an **"➕ Add to prompt" button** — sends activation tags directly to your txt2img prompt
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
- **Color legend bar** — always-visible reference above the card grid
- **NSFW badge** on cards marked as adult content (configurable)
- **"Paid" badge** (💎) for early access models
- **Model type badge** on each card
- **Tile size** — configurable card size (smaller = more cards per row)
- **Sort by date** — group cards by upload date
- **Hide installed models** — remove already-downloaded models from the grid
- **Multi-select** — checkbox on outdated cards to select multiple for batch download
- **Quick delete** on installed/outdated cards — removes model directly from the card

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
| Video playback | ON | Disable if experiencing high CPU usage |
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

> ⚠️ **Note**: This extension is designed for **Forge Neo only**. For Forge Classic or Automatic1111, use the original [sd-civitai-browser-plus](https://github.com/anxety-solo/sd-civitai-browser-plus).

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

- **Video preview not working** — the setting exists but video/gif playback in the model info panel is currently broken
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
