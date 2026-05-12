import os
import json
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Local Review Status — lightweight module for per-model review tracking
# Storage: config_states/local_review_status.json
# Schema:  {"schemaVersion": 1, "items": {"<SHA256>": { ...entry }}}
# Key:     SHA256 (uppercase, normalized)
# ---------------------------------------------------------------------------

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
