<div align="center">
  <img src=".github/logo.png?v=2" alt="CivitAI Browser Neo"/>
</div>

# 🎨 CivitAI Browser Neo

<div align="center">

[![Forge Neo](https://img.shields.io/badge/Forge-Neo-blue)](https://github.com/Haoming02/sd-webui-forge-classic/tree/neo)
[![Gradio](https://img.shields.io/badge/Gradio-4.40.0-orange)](https://gradio.app/)
[![Version](https://img.shields.io/badge/Version-1.0.0-brightgreen)](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Changelog)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Wiki](https://img.shields.io/badge/📖-Wiki-blueviolet)](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki)

> **Extension for [Stable Diffusion WebUI Forge - Neo](https://github.com/Haoming02/sd-webui-forge-classic/tree/neo)** · **[📖 Full documentation on the Wiki](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki)**

</div>

Browse, download, and manage your model library directly inside Forge Neo — multi-source discovery, a self-contained Local Models tab, LoRA categorization, auto-organization, disk usage dashboard, creator management, and support for all modern architectures (FLUX, Wan, Qwen, Krea 2, Pony, Illustrious, and more).

> [!Important]
> This extension requires **Forge Neo** (Gradio 4). For Forge Classic or Automatic1111, use the [anxety-solo fork](https://github.com/anxety-solo/sd-civitai-browser-plus) instead.

---

## 📋 Table of Contents

- [What's New](#-whats-new)
- [Features](#-features)
- [Installation](#-installation)
- [Documentation](#-documentation)
- [Credits](#-credits)

---

## 🆕 What's New

### v1.0.0 — First Stable Release

The largest update since the Neo fork: the Browser is no longer hardwired to CivitAI, the Local Models tab was rebuilt from scratch, and a LoRA categorization system ships alongside it.

- **Multi-Source Browser** — search through pluggable source adapters instead of CivitAI only: **CivArchive**, **ModelScope**, and **Arc en Ciel** join CivitAI in the source dropdown. *[→ Browser Sources](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Feature-Browser-Sources)*
- **Paste model URL** — paste a direct link from CivitAI, CivArchive, Hugging Face, ModelScope, or Arc en Ciel; the extension detects the provider and renders a card ready for download. Hugging Face direct file links, including subfolders, resolve to the exact file.
- **Local Models rebuilt** — a self-contained tab with its own state, pagination, filters, and progress bar. **Update Models is merged into it**, so scanning, batch updating, renaming, and deleting live in one place. *[→ Local Models](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Feature-Local-Models)*
- **LoraDex** — a new sub-tab for LoRA categories: auto-suggestion from tags and description, manual override saved to the `.json` sidecar, category badges, and `Lora/<base>/<category>/` subfolders. *[→ LoraDex](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Feature-LoraDex)*
- **Native Extra Networks cards** — the txt2img/img2img checkpoint and LoRA cards now carry base-model badges, LoRA category, trigger words, and the real CivitAI name, read from local sidecars with no extra API calls. An opt-in theme restyles them to look like the CivitAI website. *[→ Native Cards](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Feature-Native-Cards)*
- **Paid and Early Access are told apart** — a timed window that expires into a free download gets an aqua **Early Access** badge; a permanent Buzz purchase gets a gold **Paid** badge, each with its own hide filter. *[→ Paid vs. Early Access](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Feature-Paid-vs-Early-Access)*
- **Metadata maintenance** — **Verify local metadata** checks that cached CivitAI IDs still resolve and that `.api_info.json` matches its file; **Resolve via CivArchive** recovers metadata for models delisted from CivitAI. *[→ Metadata Maintenance](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Feature-Metadata-Maintenance)*
- **GGUF support** — `.gguf` is a first-class checkpoint format: scanned by Local Models, recognized as installed, with sidecars, delete actions, and update checks working like `.safetensors`/`.ckpt`.
- **Faster and steadier** — installed-version detection and bulk download no longer walk the model tree per card, previews can be saved as JPEG, Aria2 retries with backoff on HTTP 429, and freshly-published versions no longer show a false "Unable to load preview images" error.

📖 **[Full changelog](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Changelog)** — every release back to v0.1.0 · **[Roadmap](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Roadmap)** — what's planned for v1.1.0

---

## 🎯 Features

> ⭐ = exclusive to Neo

### 🔍 Browse & Search
*[Full details on the Wiki →](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Feature-Browser-Sources)*

- Browse CivitAI directly inside the WebUI — no tab switching
- Select a source adapter: CivitAI, CivArchive, ModelScope, or Arc en Ciel ⭐
- Search by model name, tag, username, or **paste a direct model URL** ⭐
- Filter by content type, base model, time period, and sort order — the base-model list auto-updates from CivitAI at startup ⭐
- NSFW toggle, liked-only filter, hide installed models, hide banned creators
- Independent **Hide early access** and **Hide paid** filters ⭐
- Search settings persist across restarts ⭐

### 🏠 Local Models ⭐
*[Full details on the Wiki →](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Feature-Local-Models)*

- Self-contained tab for the models installed on your machine — browse, rename, update, and delete
- Update Models merged in: outdated models get an orange border and can be updated in batch
- Pagination (25 / 50 / 100 per page), sorting, and content-type + base-model filters
- Retention policy on update: keep alongside, move to trash, or replace
- Detail panel with version dropdown, **File dropdown** for multi-file versions, trained tags with "Add to prompt", and "Download selected version"
- Resilient metadata fetch — models the API can't resolve still show as local-only cards instead of vanishing

### 🏷️ LoRA Categorization & LoraDex ⭐
*[Full details on the Wiki →](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Feature-LoraDex)*

- Paginated LoRA list with mini-thumbnails and zoom
- Categories auto-suggested from tags, description, filename, and model name
- Manual assignment per LoRA, individually or in batch, saved to the `.json` sidecar
- Category badge on model cards
- Organize LoRAs into `Lora/<base>/<category>/` subfolders — on download and in bulk

### 📥 Download
*[Full details on the Wiki →](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Feature-Downloads)*

- Download any model, version, and file variant (`.safetensors`, `.ckpt`, `.gguf`, …)
- High-speed multi-connection downloads via Aria2, with 429 backoff and auto-reconnect
- Queue that survives session disconnects, with one-click restore ⭐
- Independent progress bars for the Browser and Local Models tabs ⭐
- File integrity check with silent-update detection — a hash mismatch re-queries the API before failing ⭐
- Previews savable as PNG or JPEG ⭐
- API key support for early access, paid, and private models · proxy support for restricted regions

### 🗂️ Auto-Organization ⭐
*[Full details on the Wiki →](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Feature-Auto-Organization)*

- New downloads automatically sorted into subfolders by base model (SDXL/, Pony/, FLUX/, …)
- Modular: organize by base model, by LoRA category, or both
- Validate organization, fix misplaced files, and one-click rollback (keeps last 5 backups)
- Custom folder mapping in Settings
- Associated files (`.json`, `.png`, `.txt`) always move with the model

### 🗄️ Metadata Maintenance ⭐
*[Full details on the Wiki →](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Feature-Metadata-Maintenance)*

- **Verify local metadata** — check that cached CivitAI IDs still resolve and that `.api_info.json` matches its file
- **Resolve via CivArchive** — recover metadata for models delisted from CivitAI
- **Mark for review** — flag a local model for later attention; status stored by SHA256
- Bulk metadata, tag, and preview refresh from CivitAI

### 🖼️ Model Info & Send to txt2img
*[Full details on the Wiki →](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Feature-Model-Info)*

- Model info panel with name, version, base model, type, tags, permissions, and description
- Sample images with "Send to txt2img" — including SwarmUI → A1111 infotext conversion ⭐
- Individual meta field buttons — click to replace, Shift+click to append ⭐
- "➕ Add to prompt" appends trigger words and auto-inserts LoRA syntax ⭐
- SHA256 shown in version info · video preview on hover ⭐

### 🎴 Native Extra Networks Cards ⭐
*[Full details on the Wiki →](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Feature-Native-Cards)*

- Base-model badge, LoRA category, trigger words, and the real CivitAI name on WebUI's own txt2img/img2img cards
- Read from local sidecars — no extra API calls, no folder walk
- Opt-in **CivitAI-style card theme** restyles them to look like the CivitAI website

### 📊 Dashboard ⭐
*[Full details on the Wiki →](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Feature-Dashboard)*

- Disk usage by category and architecture, with a pie chart breakdown
- Top 10 largest files and categories · orphan file detection
- Export to CSV or JSON
- Passive CivitAI account status badge

### 🃏 Model Cards & Safety

- Color-coded borders: aquamarine = installed, orange = outdated, gold = favorite creator
- NSFW, access, type, base-model, and LoRA-category badges ⭐
- Multi-select checkboxes for batch download · quick delete · configurable tile size
- Favorite (⭐) and ban (🚫) creator directly from the card ⭐
- Deleted models go to the OS recycle bin by default · filename sanitization and length cap
- Automatic backup before organize/fix operations

---

## 📦 Installation

1. Open Forge Neo WebUI
2. Go to **Extensions** → **Install from URL**
3. Paste: `https://github.com/eduardoabreu81/sd-civitai-browser-neo`
4. Click **Install** and reload the WebUI

Requires [Forge Neo](https://github.com/Haoming02/sd-webui-forge-classic/tree/neo) (Gradio 4.40.0) and Python 3.10+.

📖 **[Installation guide on the Wiki →](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Installation)** — first-run setup, API key, and Aria2 notes

---

## 📚 Documentation

Everything lives on the **[Wiki](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki)**:

| | |
|---|---|
| **Getting started** | [Installation](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Installation) · [Settings Reference](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Settings-Reference) · [Supported Model Types](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Supported-Model-Types) |
| **Features** | [Browser Sources](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Feature-Browser-Sources) · [Local Models](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Feature-Local-Models) · [LoraDex](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Feature-LoraDex) · [Downloads & Previews](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Feature-Downloads) · [Auto-Organization](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Feature-Auto-Organization) |
| | [Metadata Maintenance](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Feature-Metadata-Maintenance) · [Paid vs. Early Access](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Feature-Paid-vs-Early-Access) · [Native Extra Networks Cards](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Feature-Native-Cards) · [Model Info & txt2img](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Feature-Model-Info) · [Dashboard](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Feature-Dashboard) |
| **Release** | [Changelog](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Changelog) · [Roadmap](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Roadmap) · [Known Issues](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki/Known-Issues) |

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

**[📖 Wiki](https://github.com/eduardoabreu81/sd-civitai-browser-neo/wiki)** • **[Report Bug](https://github.com/eduardoabreu81/sd-civitai-browser-neo/issues)** • **[Request Feature](https://github.com/eduardoabreu81/sd-civitai-browser-neo/issues)** • **[Discussions](https://github.com/eduardoabreu81/sd-civitai-browser-neo/discussions)** • **[☕ Ko-fi](https://ko-fi.com/eduardoabreu81)**

</div>
