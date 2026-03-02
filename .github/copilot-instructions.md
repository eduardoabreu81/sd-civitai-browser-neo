# CivitAI Browser Neo — Copilot Instructions

## Architecture Overview

Forge Neo WebUI extension. Python backend em `scripts/`, JS em `javascript/`, styles em `style.css`. Entry point é `scripts/civitai_gui.py` registrado via `script_callbacks.on_ui_tabs(on_ui_tabs)`.

- `javascript/civitai-html.js` — lógica client-side da aplicação
- `javascript/Sortable.min.js` — biblioteca vendor (drag-and-drop), não modificar
- `lib/` — diretório reservado para módulos futuros (atualmente vazio)

### Module Responsibilities

| File | Role |
|------|------|
| `scripts/civitai_global.py` | Shared mutable state (`gl.*`). **Every module calls `gl.init()` at import time.** |
| `scripts/civitai_api.py` | CivitAI REST API calls, HTML card/model-page generation, JSON helpers |
| `scripts/civitai_file_manage.py` | File scanning, SHA256 hash, version comparison, auto-organize, update detection |
| `scripts/civitai_download.py` | Download queue, aria2 RPC, retention policy |
| `scripts/download_log.py` | Persistência do estado da fila em `config_states/neo_download_queue.jsonl` (JSONL, ciclo: queued→downloading→completed/cancelled/failed/dismissed) |
| `scripts/civitai_gui.py` | Gradio 4.x UI layout + all event wiring (~2000 lines) |
| `javascript/civitai-html.js` | Client-side card interaction, JS→Python trigger pattern |

## Critical Patterns

### JS → Python trigger (hidden textbox bridge)
Gradio 4.x has no direct JS→Python call. The pattern throughout the codebase:

```python
# gui.py — declare hidden textbox
my_trigger = gr.Textbox(elem_id='my_trigger', visible=False)
my_trigger.change(fn=handler, inputs=[...], outputs=[...])
```
```js
// civitai-html.js — fire from JS
const trigger = document.querySelector('#my_trigger textarea');
trigger.value = String(Date.now());  // unique value forces .change event
updateInput(trigger);
```
When passing a payload (e.g. single-card update): `trigger.value = "modelId|FAMILY"`.

### Global state access
All cross-module state lives in `gl.*`. Never introduce module-level mutable variables — add to `civitai_global.py` `init()` and declare in the `global` statement.
```python
import scripts.civitai_global as gl
from scripts.civitai_global import print, debug_print  # always import these
gl.update_items  # list of outdated model dicts
gl.url_list      # dict of model_id → outdated flag (used for card border coloring)
gl.update_mode   # bool — Browser tab in Update Mode
```

### JSON helpers — always use these, never raw `json.load/dump`
```python
_api.safe_json_load(path)   # returns {} on missing/corrupt file
_api.safe_json_save(path, data)  # atomic write with error handling
```

### Gradio outputs tuple
`_api.initial_model_page()` returns a fixed **17-tuple** mapped to `page_outputs` in `civitai_gui.py`. Any new browser-state function that resets the page must return the same tuple shape. Update Mode functions return a subset tied to specific outputs.

### Settings access
All user settings are read via `opts.civitai_neo_*`:
```python
from modules.shared import opts
getattr(opts, 'precise_version_check', True)  # use getattr with default — setting may not exist yet
getattr(opts, 'civitai_neo_update_retention', 'replace')
```

### Version / outdated detection
Uses **CivitAI `baseModel` field** (e.g. `"Pony"`, `"Illustrious"`) as family key + **array index in `modelVersions`** as version order (index 0 = newest — CivitAI API contract).  
**Do NOT use `extract_version_from_ver_name` for update detection** — it only matches version at end of string and fails on formats like `"v2 Pony"`, `"Illustrious v1.2"`. That function is kept only for legacy display purposes.

### Download log (JSONL persistence)
`scripts/download_log.py` é independente de `civitai_download.py` — não importa `gl` nem `opts`. Gerencia exclusivamente o arquivo `config_states/neo_download_queue.jsonl`.

```python
import scripts.download_log as _log

_log.upsert(item)          # adiciona ou atualiza entrada (por model_id + version_name)
_log.mark_status(entry_id, 'completed')  # transição de estado
_log.get_pending()         # retorna entradas com status 'queued' ou 'downloading'
_log.purge_old(days=7)     # remove entradas antigas concluídas/canceladas
```

Ciclo de vida de uma entrada: `queued → downloading → completed | cancelled | failed | dismissed`  
Use `dismissed` quando o usuário rejeitar o banner de restauração — nunca delete entradas diretamente.

### Print convention
```python
from scripts.civitai_global import print, debug_print
print("message")        # → [CivitAI Browser Neo] - message
debug_print("message")  # only when opts.civitai_neo_debug_prints is True
```

## Data Flow: Update Detection

```
file_scan() [civitai_file_manage.py]
  → version_match(file_paths, api_response)
      uses: installed SHA256 → modelVersionId → baseModel + index
  → outdated_set  →  gl.url_list  →  browser card orange borders
                  →  gl.update_items  →  Update Mode cards
                  →  last_update_scan  →  Dashboard banner
```

## Key Conventions

- **Multi-family models** (e.g. DollFace PONY + IL): produce **two separate entries** in `gl.update_items`, one per `baseModel`.
- **Card borders** are set client-side in `civitai-html.js` by checking `gl.url_list` values injected into card HTML as `data-*` attributes.
- **Gradio `.then()` chaining** is used for multi-step UI flows (e.g. scan → enter_update_mode sets `update_mode_banner`).
- **`from modules.shared import opts`** — always available inside Forge; never mock or import differently.
