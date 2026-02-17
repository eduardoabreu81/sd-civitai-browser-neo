# 🎨 CivitAI Browser Neo

[![Forge Neo](https://img.shields.io/badge/Forge-Neo-blue)](https://github.com/Haoming02/sd-webui-forge-classic/tree/neo)
[![Gradio](https://img.shields.io/badge/Gradio-4.40.0-orange)](https://gradio.app/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Extension for [Stable Diffusion WebUI Forge - Neo](https://github.com/Haoming02/sd-webui-forge-classic/tree/neo)**

Modern fork of sd-civitai-browser-plus optimized for Forge Neo with auto-organization features and support for latest model architectures (FLUX, Pony, Illustrious, Wan, Qwen, Z-Image, and more).

---

## 📋 Table of Contents

- [Neo Versioning](#-neo-versioning)
- [What's New](#-whats-new--v040)
- [SD Civitai Browser Neo Release Story](#-sd-civitai-browser-neo-release-story)
- [Roadmap](#%EF%B8%8F-roadmap)
- [What's New in Neo?](#-whats-new-in-neo)
- [Features](#-features)
- [Installation](#-installation)
- [Auto-Organization System](#-auto-organization-system)
- [Dashboard & Statistics](#-dashboard--statistics)
- [Supported Model Types](#-supported-model-types)
- [Settings](#%EF%B8%8F-settings)
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

## 🆕 What's New — v0.4.0

> **Update Intelligence** — smarter update detection, audit trail, and retention control.

- **Dashboard update summary banner** — after running a scan, the Dashboard shows a live banner: ✅ green (all up to date) or ⚠️ orange with per-type breakdown (e.g. *Checkpoint: 2, LORA: 5*)
- **Batch update from cards** — outdated cards (orange border) now show a **checkbox** instead of a delete button, enabling multi-select for batch download via the existing queue pipeline
- **Retention policy** — new setting in *Model Organization*: `keep` both files, `move to _Trash` (subfolder next to old file), or `replace` (delete old before downloading new)
- **Audit log** — every update scan and every retention action is appended to `neo_update_audit.jsonl` at the extension root for traceability

---

## 📖 SD Civitai Browser Neo Release Story

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

### v0.4.0 — Update Intelligence *(released)*
- Dashboard update summary banner (outdated count per type)
- Outdated cards show checkbox for batch update selection
- Retention policy: `keep` / `move to _Trash` / `replace`
- `neo_update_audit.jsonl` audit log

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

## ✨ What's New in Neo?

### 🚀 **Major Features**

#### **1. Smart Auto-Organization** 📁
Automatically organize your models into subfolders by type (SDXL, Pony, FLUX, etc.):
- **Auto-organize downloads**: New downloads go directly to organized folders
- **Organize existing models**: One-click organization of all your models
- **Backup & Rollback**: Safe organization with automatic backup and undo functionality
- **Customizable categories**: Define your own folder structure and detection patterns

#### **2. Modern Model Support** 🎯
Full support for all Forge Neo architectures:
- **SD**: SD1.x and SD2.x (unified)
- **SDXL**: Including Pony and Illustrious variants
- **FLUX**: Dev, Krea, Kontext, Klein (4B/9B)
- **Wan**: Wan 2.2 (T2V, I2V)
- **Qwen**: Qwen-Image, Qwen-Image-Edit
- **Z-Image**: Z-Image, Z-Image-Turbo
- **Lumina**: Neta-Lumina, NetaYume-Lumina
- **Anima**, **Cascade**, **PixArt**, **Playground**
- **SVD**, **Hunyuan**, **Kolors**, **AuraFlow**, **Chroma**

#### **3. Gradio 4.x Migration** 🔄
- Complete migration to Gradio 4.40.0 (Forge Neo compatible)
- Modern UI components and improved performance
- Better error handling and stability

#### **4. Dashboard & Statistics** 📊
Get comprehensive insights into your model collection:
- **Disk usage statistics**: See how much space each model type uses
- **File count by category**: Know exactly what you have
- **Organized by baseModel**: Checkpoints and LORAs grouped by type (Pony, SDXL, FLUX, etc.)
- **Visual breakdown**: Progress bars and percentage indicators
- **All model types**: Supports Checkpoints, LORAs, VAEs, Upscalers, ControlNets, and more
- **Smart detection**: Auto-detects organization from folder structure

#### **5. Safety Features** 🛡️
- **Automatic backups** before any organization
- **One-click rollback** to undo changes
- **Backup history** (keeps last 5 operations)
- **Safe execution** (cancels if backup fails)

---

## 🎯 Features

### Core Features (from Original)

<details open>
<summary><b>Browse & Download</b></summary>

- 🧩 **Browse all models** from CivitAI
- 📥 **Download any model**, version, and file
- 🚄 **High-speed downloads** with Aria2
- 📊 **Queue system** for batch downloads
- 🏷️ **Auto-tag** installed models
- 🔍 **Search by hash** to identify unknown models

</details>

<details open>
<summary><b>Model Management</b></summary>

- 📁 **Auto-organize** by model type (NEW in Neo!)
- ↶ **Undo organization** with one click
- 💾 **Automatic backups** before changes
- 🗂️ **Custom categories** for organization
- � **Dashboard statistics** - View disk usage by type (NEW!)
- �🔄 **Update model info & tags**
- 🖼️ **Download preview images**
- 📋 **Generate model info HTML**

</details>

<details open>
<summary><b>Integration</b></summary>

- 🎨 **Quick access** from txt2img/img2img
- 📤 **Send prompts** to txt2img
- 🔗 **CivitAI API** integration
- ⚙️ **Extensive settings**

</details>

### Improvements from Anxety-Solo Fork

- 🎨 Modern, redesigned model cards
- 📅 Neat brick-style date sorting
- 🏷️ Visual badges for model type and NSFW
- 💎 Gold badges for paid models
- 🔍 Exact search toggle
- 🖼️ Customizable preview resolution
- 📱 Better responsive design
- 🐛 Multiple bugfixes from community issues

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

## ⚙️ Settings

### Model Organization (New!)

| Setting | Description | Default |
|---------|-------------|---------|
| **Auto-organize downloads** | Automatically organize new downloads into subfolders | OFF |
| **Create "Other" folder** | Put unrecognized models in "Other/" folder | ON |
| **Custom categories** | JSON with custom folder names and patterns | (empty) |

### Browser Settings

| Setting | Description |
|---------|-------------|
| **Personal API key** | Your CivitAI API key (required for some downloads) |
| **Hide early access** | Hide early access models from results |
| **Hide dot subfolders** | Hide folders starting with `.` |
| **Use local HTML** | Use local HTML files instead of CivitAI links |
| **Page navigation header** | Keep page navigation always visible |
| **Video playback** | Enable gif/video playback in browser |
| **Resize preview cards** | Resize preview images for faster loading |

### Download Settings

| Setting | Description |
|---------|-------------|
| **Download method** | Choose between Default or Aria2 |
| **Aria2 connections** | Number of connections for Aria2 (1-64) |
| **Auto-save images** | Automatically download preview images |
| **Image count** | Number of images to save (4-64) |
| **Unpack ZIP** | Automatically extract .zip files |
| **Save HTML on download** | Save HTML file with model info |

---

##  Known Issues

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
