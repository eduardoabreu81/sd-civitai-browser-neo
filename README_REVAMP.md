# 🧪 CivitAI Browser Neo — Revamp v0.1.0

> **Active development branch `revamp`. Not yet merged into `main`.**
>
> This document describes the **Beta-Revamp v0.1.0** work-in-progress. For the current released version see [`README.md`](README.md).

---

## What is the Revamp?

The `revamp` branch is a major iteration of CivitAI Browser Neo focused on **advanced curation**, **multi-source discovery**, and **local-library ergonomics**. It keeps the existing CivitAI-first architecture intact (CivitAI remains the source of truth for metadata and SHA256 validation) and adds new browser sources, a redesigned Local Models tab, LoRA category management, and deeper Forge Neo integration.

**Branch:** `revamp`  
**Diverged from `main` at:** `a02e944`  
**Badge shown in UI:** `Beta-Revamp v0.1.0`

---

## 🌐 Multi-Source Browser

The Browser tab is no longer hardwired to CivitAI. It can route searches through pluggable source adapters and can also fetch a single model from a pasted URL.

### Browser Source selector

A dropdown in the Browser tab lets you choose the active source:

| Source | Status | Notes |
|---|---|---|
| **CivitAI** | Primary | Full native support, API key, SHA256 validation, previews, permissions, update checks. |
| **CivArchive** | Active | Mirror/backup of CivitAI records; supports the **Deleted from CivitAI** filter. |
| **ModelScope** | Active | Search/browse adapter for modelscope.cn; content type and base model detected from tags/metadata and normalized to Browser cards. |
| **Arc en Ciel** | Active | External adapter for arcenciel.io; search, pagination, detail panel, and download validated in Forge Neo. |
| **Hugging Face** | URL-only | Browsing HF search results was too noisy, so discovery moved to **Paste model URL**. The adapter remains registered but is hidden from the source dropdown. |

### Paste model URL

Switch the Browser search mode to **URL** and paste any supported link:

- `civitai.com/models/...` or `civitai.red/models/...`
- `civitai.com/api/...`
- `civarchive.com/...`
- `huggingface.co/<owner>/<repo>` (repo root)
- `huggingface.co/<owner>/<repo>/blob/main/<sub/folder/file.safetensors>` (direct file link, including subfolders)
- `modelscope.cn/models/...`
- `arcenciel.io/models/...`

The extension detects the provider, fetches the model, renders a single card, and populates the model panel for download. For Hugging Face file links, the exact file is selected as the primary download and its real size is fetched from the resolve URL.

### External-source provenance

Non-CivitAI cards and detail panels can display:

- Origin source badge
- Source URL / mirror notes
- Download provenance
- Normalized metadata so external files/images work with the legacy detail-panel flow, sidecars, and preview saving

### Source-specific behavior

- **Deleted from CivitAI** only applies to CivArchive. It means CivArchive marks the model as removed from CivitAI; it does not mean "exclusive to another platform".
- **Not found on CivitAI** is planned separately and requires a cross-source SHA256 double-check.
- External-source file/image metadata is normalized to the same shape CivitAI uses, so size, format, and preview handling stay compatible.

---

## 🏠 Local Models Redesign

The Local Models tab has been rebuilt to be self-contained and faster.

### Self-contained tab

- Own state, pagination, filters, and progress bar — independent from the Browser tab.
- Update Models has been merged into Local Models.
- Multi-select checkboxes work correctly across pages for batch update/delete.

### Pagination

- Per-page controls: **25 / 50 / 100** cards.
- Server-side slicing of the cached model list, so sorting and page changes are instant.
- Previous / Next buttons plus a page slider.

### Hybrid local fetch

- CivitAI `/models` batched requests with per-id fallback when a single model poisons a batch.
- Version-endpoint recovery for huge models that 500 the `/models` endpoint.
- Automatic fallback `civitai.com` → `civitai.red`.
- Models that cannot be resolved from the API are shown as local-only fallback cards instead of disappearing.

### Detail panel improvements

- Trained tags with **Add to prompt** button.
- Version dropdown refreshes the panel when changed.
- **Download selected version** button for versions not currently installed.
- **File dropdown** lets you pick the exact file/variant when a version has multiple files; filename and SHA256 update accordingly.
- Detail panel state is isolated from the Browser tab.

### Update Models inside Local Models

- Orange border on outdated models.
- Batch update with multi-select.
- Version selection respects base-model family.
- Retention policy on update: keep, move to trash, or replace.

---

## 🃏 LoRA Categorization & LoraDex

A new sub-tab inside Local Models for managing LoRA categories.

### LoraDex

- Paginated list of local LoRAs with mini-thumbnails and zoom.
- Manual category assignment per LoRA.
- Apply/Reset individual or in batch.
- Persistence saved to the `.json` sidecar as `loraCategory`.

### Auto-categorization

- `categorize_lora_by_tags()` suggests categories from tags + description.
- Categories include: Character, Style, Clothing, Pose, Background, Concept, Tool, Slider, and more.
- Manual `loraCategory` in the sidecar wins over auto-detection.

### Category badge

- LoRA cards show their category badge below the model-type badge.
- Organization and download respect the manual category when `civitai_neo_lora_category_sort` is enabled.

### Organization by category

- New downloads and bulk organization can sort LoRAs into `Lora/<base>/<category>/` subfolders.
- Combines with existing base-model organization or works independently.

---

## 📥 Download & Preview Improvements

### Preview format

- Setting `preview_format` lets you save previews as **JPEG**.
- `preview_jpeg_quality` controls quality.
- When switching to JPEG, old `.preview.png`/`.png` files are automatically removed.

### Aria2 resilience

- Automatic retry with backoff when CivitAI returns **HTTP 429**.
- Timeout increased to 30s with up to 3 retries for network failures.
- SHA256 verification buffer increased from 1MB to 8MB.
- Internal queue loop eliminates Gradio event-queue gaps between queued items.

### Silent update detection

- If a downloaded file fails SHA256 verification, the extension re-queries `/api/v1/model-versions/{version_id}`.
- If the author silently updated the file, the new hash is accepted and metadata is refreshed instead of failing.

### Paid vs. Early Access

CivitAI gates downloads two different ways, and they used to be reported identically as
"Early Access". They now have separate badges, labels, and filters:

| Kind | API shape | Card badge | Becomes free? |
|---|---|---|---|
| Early Access | `paidAccess: {permanent: false, endsAt: <future>}` | aqua **Early Access** | **Yes**, when the window closes |
| Paid | `paidAccess: {permanent: true, endsAt: null}` | gold **Paid** | **No**, ever |
| Paid | `paidAccess: {permanent: false, endsAt: null}` | gold **Paid** | **No** published date to wait for |

- A **populated `paidAccess` object is itself the gate signal**; its fields only say
  *which* gate. All three shapes above occur in the wild (counted over 1660 live
  versions: 49 timed, 15 permanent, 1 dateless). The dateless shape is rare but real —
  it is reported as **Paid**, not Early Access, because with no date there is nothing to
  wait for and an "it becomes free later" label would be a lie.
- An `endsAt` in the **past** means the window already closed → genuinely free again.
- `get_access_kind()` (`scripts/civitai_api.py`) is the single classifier; `permanent` is
  evaluated before `endsAt`, so a stale end date cannot downgrade a permanent purchase.
- `availability` is no longer usable as a signal: `/api/v1/model-versions/{id}` returns it
  as `null`, and the list endpoint returns `"Public"` for **both** gated kinds. Only
  `paidAccess` is authoritative. Legacy `availability: 'EarlyAccess'` and
  `earlyAccessEndsAt` are still honored for older/mirrored payloads.
- Version dropdown suffixes: `(Early Access)` vs `(Paid)` — one model can mix free,
  early-access and paid versions.
- Detail panel: *"Early Access (free after YYYY-MM-DD)"* vs *"Paid (Buzz purchase)"*.
- The download pre-flight guard blocks the request and names the gate, instead of letting
  CivitAI's silent redirect to the purchase page reach Aria2 as an `Unrecognized URI` error.
- Two independent settings: **Hide early access models** and **Hide paid models**.
  ⚠️ These were one setting before; the first no longer hides permanently-paid versions.

### Preview gallery reliability

- A freshly-published model version no longer shows a false "Unable to load preview images" error — the extension retries through a second endpoint (and, as a last resort, the images already fetched for the model page) instead of giving up on the first failed request.
- That retry preserves full per-image generation data (prompt, sampler, steps, CFG, seed) instead of falling back to bare thumbnails with no metadata.
- The Local Models detail panel now detects a cached preview that's stuck in that error state and rebuilds it automatically on the next click, instead of showing the same broken cache indefinitely.
- Fixed a bug where updating an already-installed model with **"Replace installed"** could regenerate the `.html`/`.json` sidecar with the *previous* version's data instead of the new one — the extension was resolving metadata against whichever version was still marked installed on disk at that moment, rather than the version actually being downloaded.

---

## 🗂️ Organization Enhancements

### Modular organization

- Organize by **base model**, by **LoRA category**, or both.
- Custom categories can be defined in **Settings → Model Organization** with a JSON pattern list.
- Wan models can be split into `Wan/I2V/`, `Wan/T2V/`, `Wan/TI2V/` subfolders.
- `.json` sidecars now persist the raw `baseModel` value (in addition to the legacy `sd version` field) so organization and installed-status detection stay reliable.
- Auto-organize has a defensive recalculation: if a download is about to land in a content-type root folder because the detail panel has not yet refreshed, the extension fetches the model's `baseModel` and redirects it to the correct subfolder.

### New supported base models

The base-model dropdown, badges, and organization categories are kept in sync with CivitAI API values:

- **Krea 2** — badge `Krea2`
- **LTXV** — badge `LTX`
- **Ernie** — badge `Ernie`
- **Anima**
- **Chroma**
- **Z-Image** / **Z-Image Turbo** — badges `ZIB` / `ZIT`
- Existing: SD 1.x, SDXL, Pony, Illustrious, NoobAI, FLUX, Wan, Qwen, Lumina, etc.

> **Krea 2 note:** `krea2_turbo_fp8_scaled.safetensors` requires the Qwen-Image VAE (`qwen_image_vae.safetensors`) and the Qwen3VL 4B text encoder (`qwen3vl_4b_fp8_scaled.safetensors`), not FLUX text encoders. Place both files in `models/text_encoder/`.

### GGUF support

- `.gguf` is supported as a checkpoint format.
- `.gguf` files are scanned by Local Models.
- Browser cards recognize `.gguf` as installed and resolve its `.json`/`.api_info.json` sidecars.
- Download, organization, local review, and metadata flows handle `.gguf` safely.

---

## 🔑 Account Badge (MCP)

The Dashboard shows a passive account-status badge via `scripts/civitai_mcp.py`. It auto-connects with the saved API key and displays the connected CivitAI username (or a connection warning). No actions are tied to the badge.

---

## 🎨 Model Info & Send to txt2img

- Send-to-txt2img always emits a **Negative prompt** line, even if the card only has a positive prompt.
- Individual meta-field buttons: click to replace, Shift+click to append.
- SwarmUI embedded params are converted to A1111 infotext format.
- Cached HTML sidecars get their stale Send-to-txt2img buttons rewired.

---

## 🛡️ Safety

- Recycle-bin deletion by default (`send2trash`).
- Automatic backup before organize/fix operations (keeps last 5).
- Filename sanitization and length cap.
- Conflict detection (skips existing files).
- Associated files (`.json`, `.png`, `.txt`) always move with the model.

---

## ⚠️ Known Issues & Limitations

- Update detection is still somewhat sensitive to filename/name matching and may miss some outdated models.
- `nsfwLevel` checks are not 100% accurate.
- ModelScope content-type/base-model detection is heuristic and may misclassify unusual models.
- Cross-source SHA256 double-check and a separate **Not found on CivitAI** filter are still pending (Phase F).
- Hugging Face remains URL-only until a curated catalog is built.

---

## 🗺️ Revamp Roadmap

### ✅ Complete
- Multi-Source Browser foundation (CivArchive, Hugging Face, Arc en Ciel, ModelScope)
- Paste-model-URL mode
- Local Models self-contained + pagination
- Update Models merged into Local Models
- LoraDex + LoRA category management
- Preview JPEG format + Aria2 429 retry
- New base models synced with CivitAI (Krea 2, LTXV, Ernie, Anima, Chroma, Z-Image)
- Explicit GGUF support
- Passive account badge on the Dashboard via MCP

### 🚧 In Progress / Planned
- Cross-source SHA256 double-check
- **Not found on CivitAI** filter
- Hugging Face curated catalog foundation
- Saved search presets
- Favorites in creator/user search
- Organization by Tag (phases 1 & 2)
- Additional direct adapters (TensorArt, SeaArt, PixAI, Shakker, Tungsten, Civision, TensorHub, Yodayo, Moescape)

---

## 🤝 Relationship to `main`

- `main` stays at **v0.9.0** until the revamp is merged.
- The `revamp` branch is developed in-place; install it by switching to the `revamp` branch or installing from the branch URL.
- CivitAI remains the primary source of truth for metadata and SHA256 validation; external sources are added incrementally and should be runtime-tested in Forge Neo before release.
