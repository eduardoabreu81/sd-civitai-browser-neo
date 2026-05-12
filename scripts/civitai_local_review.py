import os
import json
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Local Review Status — lightweight module for per-model review tracking
# Storage: config_states/local_review_status.json
# Schema:  {"schemaVersion": 1, "items": {"<SHA256>": { ...entry }}}
# Key:     SHA256 (uppercase, normalized)
# ---------------------------------------------------------------------------

# Attempt to reuse the Forge Neo helper; fall back to a local implementation
# for standalone test environments where modules.shared is unavailable.
try:
    from scripts.civitai_api import safe_json_load
except ImportError:
    def safe_json_load(file_path):
        """Safely load JSON file with error handling (local fallback)."""
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

# Attempt to import content-type detector from file_manage.
# If Forge Neo modules are unavailable, leave as None and skip detection.
try:
    from scripts.civitai_file_manage import _detect_content_type_from_path
except ImportError:
    _detect_content_type_from_path = None


REVIEW_FILE = os.path.join(os.getcwd(), 'config_states', 'local_review_status.json')
_CURRENT_SCHEMA = 1

_VALID_STATUSES = frozenset({
    'needs_review',
    'manual_delete_candidate',
    'manual_keep',
})


def _normalize_sha256(sha256):
    """Normalize SHA256 to uppercase stripped string."""
    return (sha256 or '').upper().strip()


def _now_iso():
    """Return current UTC time in ISO-8601 format with Z suffix."""
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _normalize_reasons(reasons):
    """
    Normalize a reasons list:
    - accept list or None
    - strip each string
    - remove empty strings
    - remove duplicates while preserving order
    """
    if not reasons:
        return []
    seen = set()
    out = []
    for r in reasons:
        if not isinstance(r, str):
            continue
        s = r.strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _make_empty_data():
    """Return a fresh, valid versioned data structure."""
    return {
        'schemaVersion': _CURRENT_SCHEMA,
        'items': {},
    }


def load_local_review_status():
    """
    Load the review-status JSON from disk.
    Always returns a valid versioned structure:
        {"schemaVersion": 1, "items": {...}}

    If the file is missing or corrupt, returns an empty structure.
    If the file is in the legacy flat format (direct SHA256 keys),
    it is accepted and migrated in memory to the new format.
    """
    if not os.path.exists(REVIEW_FILE):
        return _make_empty_data()

    try:
        with open(REVIEW_FILE, 'r', encoding='utf-8') as f:
            raw = json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        return _make_empty_data()

    if not isinstance(raw, dict):
        return _make_empty_data()

    # Already versioned
    if 'schemaVersion' in raw and 'items' in raw:
        if isinstance(raw.get('items'), dict):
            return raw
        # malformed items -> fix in memory
        return _make_empty_data()

    # Legacy format: direct SHA256 keys at root level
    # Migrate in memory (save will write the new schema)
    migrated = _make_empty_data()
    for key, value in raw.items():
        if isinstance(value, dict):
            migrated['items'][_normalize_sha256(key)] = value
    return migrated


def save_local_review_status(data):
    """
    Persist the review-status dict to disk.
    Creates config_states/ automatically if needed.
    Ensures the data carries the current schemaVersion before writing.
    """
    if not isinstance(data, dict):
        raise ValueError("data must be a dict")

    data.setdefault('schemaVersion', _CURRENT_SCHEMA)
    if 'items' not in data or not isinstance(data['items'], dict):
        data['items'] = {}

    directory = os.path.dirname(REVIEW_FILE)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(REVIEW_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _build_review_button_html(model_file):
    """Build a review button snippet for the overlay HTML.

    Reads local sidecars to determine if the model is already marked for review.
    No API calls, no SHA256 generation, no sidecar writes, no global state mutation.
    """
    if not model_file or not os.path.isfile(model_file):
        return ''
    try:
        meta = _resolve_local_model_meta(model_file)
        sha256 = meta.get('sha256')
        already_marked = bool(sha256 and get_review_status(sha256))
    except Exception:
        already_marked = False

    escaped_path = model_file.replace('\\', '\\\\').replace("'", "\\'")
    if already_marked:
        return (
            '<div class="review-block" style="margin-top:16px;padding:12px;border-top:1px solid #444;">'
            '<button disabled style="opacity:0.6;cursor:not-allowed;">'
            'Marked for review ✅'
            '</button></div>'
        )
    return (
        '<div class="review-block" style="margin-top:16px;padding:12px;border-top:1px solid #444;">'
        f'<button class="mark-review-btn" onclick="markForReviewOverlay(&quot;{escaped_path}&quot;)">'
        'Mark for review'
        '</button></div>'
    )


def _inject_review_block_into_model_html(output_html, review_html):
    """Inject review_html before the closing of the main-container div.

    Falls back to returning the original HTML if the injection point cannot be
    determined safely.  The overlay HTML is known to end with a single top-level
    <div class="main-container">…</div>, so we look for the last </div>.
    """
    if not review_html:
        return output_html
    if not output_html or 'class="main-container"' not in output_html:
        return output_html
    last_close = output_html.rfind('</div>')
    if last_close == -1:
        return output_html
    return output_html[:last_close] + review_html + output_html[last_close:]


def get_review_status(sha256):
    """
    Retrieve the review entry for a given SHA256.
    Returns an empty dict if the SHA256 is unknown.
    """
    data = load_local_review_status()
    key = _normalize_sha256(sha256)
    return data['items'].get(key, {}) if key else {}


def mark_for_review(item):
    """
    Create or update a review entry keyed by the item's SHA256.

    Expected fields in *item* (all optional except sha256):
        sha256, status, reasons, manualNote,
        modelId, modelVersionId, fileName, filePath,
        contentType, baseModel, modelName, versionName

    Existing fields are preserved when not provided in *item*.
    *updatedAt* is always refreshed to the current UTC time.
    *reasons* are normalized (stripped, deduplicated, empties removed).
    *status* defaults to "needs_review".

    Returns the saved entry dict.
    """
    if not isinstance(item, dict):
        raise ValueError("item must be a dict")

    key = _normalize_sha256(item.get('sha256'))
    if not key:
        raise ValueError("sha256 is required")

    data = load_local_review_status()
    existing = data['items'].get(key, {})

    incoming_status = item.get('status', existing.get('status', 'needs_review'))
    if incoming_status not in _VALID_STATUSES:
        # Allow unknown statuses to pass through (forward compatibility),
        # but coerce missing/empty to the default.
        if not incoming_status:
            incoming_status = 'needs_review'

    entry = {
        'status': incoming_status,
        'reasons': _normalize_reasons(
            item.get('reasons', existing.get('reasons', []))
        ),
        'manualNote': item.get('manualNote', existing.get('manualNote', '')),
        'updatedAt': _now_iso(),
        'modelId': item.get('modelId', existing.get('modelId')),
        'modelVersionId': item.get('modelVersionId', existing.get('modelVersionId')),
        'fileName': item.get('fileName', existing.get('fileName')),
        'filePath': item.get('filePath', existing.get('filePath')),
        'contentType': item.get('contentType', existing.get('contentType')),
        'baseModel': item.get('baseModel', existing.get('baseModel')),
        'modelName': item.get('modelName', existing.get('modelName')),
        'versionName': item.get('versionName', existing.get('versionName')),
    }

    # Drop None values to keep the JSON clean and minimal.
    entry = {k: v for k, v in entry.items() if v is not None}

    data['items'][key] = entry
    save_local_review_status(data)
    return entry


def _resolve_local_model_meta(file_path):
    """
    Read local metadata for a single model file without network calls,
    bulk scans, sidecar writes, or global state mutation.

    Sources (in priority order):
      1. {file}.json sidecar       -> sha256, modelId, modelVersionId
      2. {file}.api_info.json      -> baseModel, versionName, modelName
      3. Path inference            -> contentType, fileName, filePath

    Returns a dict with all available fields; missing fields are omitted
    to keep the output minimal and clean.
    """
    if not file_path or not str(file_path).strip():
        raise ValueError("file_path is required")

    result = {}

    # Basic path info
    result['fileName'] = os.path.basename(file_path)
    result['filePath'] = file_path

    # Content type from path (only when Forge Neo environment is available)
    if _detect_content_type_from_path is not None:
        ct = _detect_content_type_from_path(file_path)
        if ct and ct != 'Other':
            result['contentType'] = ct

    # --- 1. Read .json sidecar ------------------------------------------------
    json_path = os.path.splitext(file_path)[0] + '.json'
    json_data = safe_json_load(json_path)

    if json_data and isinstance(json_data, dict):
        sha256 = json_data.get('sha256')
        if sha256:
            result['sha256'] = sha256.upper().strip()

        model_id = json_data.get('modelId')
        if model_id is not None:
            result['modelId'] = model_id

        model_version_id = json_data.get('modelVersionId')
        if model_version_id is not None:
            result['modelVersionId'] = model_version_id

        # Fallback baseModel from "sd version" (may be stale; lower priority)
        sd_version = json_data.get('sd version', '').strip()
        if sd_version and sd_version.upper() != 'OTHER':
            result['baseModel'] = sd_version

    # --- 2. Read .api_info.json -----------------------------------------------
    api_info_path = os.path.splitext(file_path)[0] + '.api_info.json'
    api_data = safe_json_load(api_info_path)

    if api_data and isinstance(api_data, dict):
        # baseModel: .api_info.json wins over "sd version"
        base_model = api_data.get('baseModel', '').strip()
        if not base_model:
            base_model = api_data.get('model', {}).get('baseModel', '').strip()
        if not base_model and api_data.get('modelVersions'):
            versions = api_data.get('modelVersions', [])
            if versions:
                base_model = versions[0].get('baseModel', '').strip()
        if not base_model:
            base_model = api_data.get('version', {}).get('baseModel', '').strip()
        if base_model:
            result['baseModel'] = base_model

        # versionName
        version_name = api_data.get('name', '').strip()
        if version_name:
            result['versionName'] = version_name

        # modelName
        model_name = api_data.get('model', {}).get('name', '').strip()
        if model_name:
            result['modelName'] = model_name

        # Fallback modelId / modelVersionId from api_info if missing from .json
        if 'modelId' not in result:
            api_model_id = api_data.get('modelId')
            if api_model_id is not None:
                result['modelId'] = api_model_id
        if 'modelVersionId' not in result:
            api_version_id = api_data.get('id')
            if api_version_id is not None:
                result['modelVersionId'] = api_version_id

    return result


def mark_file_for_review(file_path, reasons=None, manual_note=''):
    """
    Mark a local model file for review by resolving its metadata from sidecars
    and saving a review entry keyed by its SHA256.

    Args:
        file_path: Absolute or relative path to the model file.
        reasons:   Optional list of reason strings (will be normalized).
        manual_note: Optional free-text note.

    Returns:
        The saved review entry dict (same shape as mark_for_review output).

    Raises:
        ValueError: If file_path is invalid or if no sha256 could be resolved.
    """
    meta = _resolve_local_model_meta(file_path)

    sha256 = meta.get('sha256')
    if not sha256:
        raise ValueError(
            f"Cannot mark for review: no sha256 found for '{file_path}'. "
            "Ensure the model has a .json sidecar with a sha256 field."
        )

    item = {
        'sha256': sha256,
        'status': 'needs_review',
        'reasons': reasons,
        'manualNote': manual_note,
    }

    # Merge resolved metadata fields when present
    for key in ('modelId', 'modelVersionId', 'fileName', 'filePath',
                'contentType', 'baseModel', 'modelName', 'versionName'):
        if key in meta:
            item[key] = meta[key]

    return mark_for_review(item)


def clear_review_status(sha256):
    """
    Remove the review entry for the given SHA256.
    Returns True if an entry was removed, False otherwise.
    """
    data = load_local_review_status()
    key = _normalize_sha256(sha256)
    if key and key in data['items']:
        del data['items'][key]
        save_local_review_status(data)
        return True
    return False
