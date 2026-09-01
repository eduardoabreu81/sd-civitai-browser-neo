"""Path helpers for the Organization tab.

Kept free of gradio / WebUI imports on purpose: civitai_file_manage cannot be
imported outside Forge, so the logic that decides *where a model file belongs*
lives here where the tests can reach it directly (same reasoning as
scripts/browser_sources).
"""

import os

# Category subfolder names the organizer may create under a model root.
# 'Auto' and 'None' are LoraDex dropdown states, not folders, so they are
# deliberately absent — see civitai_file_manage.LORA_DEX_CATEGORIES.
CATEGORY_FOLDER_NAMES = frozenset({
    'Character', 'Style', 'Clothing', 'Concept',
    'Pose', 'Background', 'Utility', 'Slider',
})

# Content types whose files are LoRAs and may therefore get a category subfolder.
LORA_CONTENT_TYPES = frozenset({'LORA', 'LoCon', 'DoRA'})


def _normalized(path):
    """Comparable form of a path: symlinks resolved, case folded on Windows.

    list_files() walks with followlinks=True, so a file reached through a
    symlinked folder must still match the root it actually lives under.
    """
    if path is None:
        return None
    try:
        return os.path.normcase(os.path.realpath(str(path)))
    except (OSError, ValueError):
        return os.path.normcase(os.path.normpath(str(path)))


def resolve_model_root(file_path, roots):
    """Return the configured model root that contains file_path.

    ``roots`` is an iterable of (root_path, content_type) pairs. The longest
    matching root wins, so nested configurations (a --lora-dirs entry inside
    models/Lora, say) resolve to the most specific one rather than whichever
    happened to be listed first.

    Returns (root_path, content_type) exactly as supplied by the caller, or
    (None, None) when the file lives under none of them.

    Replaces the old "walk up until a folder is literally named Lora" scan,
    which silently failed for every user whose --lora-dir points somewhere with
    a different name: the walk hit the filesystem root, fell back to the file's
    own directory, and the organizer then created its Base/Category folders
    *inside* the user's existing subfolders.
    """
    target = _normalized(file_path)
    if not target:
        return None, None

    best_root = None
    best_type = None
    best_len = -1

    for root_path, content_type in roots or []:
        root_norm = _normalized(root_path)
        if not root_norm:
            continue
        # Guard against 'C:/loras-old' matching a file under 'C:/loras'.
        prefix = root_norm.rstrip(os.sep) + os.sep
        if target == root_norm or target.startswith(prefix):
            if len(root_norm) > best_len:
                best_root = root_path
                best_type = content_type
                best_len = len(root_norm)

    return best_root, best_type


def category_from_current_folder(file_path):
    """Return the category implied by the folder a file already sits in.

    The organizer applies its heuristic on every scan and never records the
    result anywhere — the folder on disk *is* the stored category. So when the
    heuristic declines to classify a file that already lives in, say,
    ``Lora/Anima/Slider/``, treating that folder as a confirmed category is what
    keeps an already-organized library from being shuffled back out on the next
    run. Returns None when the parent folder is not a category name.
    """
    parent = os.path.basename(os.path.dirname(str(file_path)))
    return parent if parent in CATEGORY_FOLDER_NAMES else None
