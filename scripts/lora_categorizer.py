"""Heuristic LoRA categorization.

Kept free of gradio / WebUI imports on purpose: civitai_file_manage cannot be
imported outside Forge, so the classification rules live here where the tests can
reach them directly (same reasoning as scripts/browser_sources).

Replaces a first-match-wins substring scan that misfiled LoRAs in bulk. CivitAI
user ODSP1994, who requested the feature, reported it plainly:

    "the system does get confused with some style loras being classified as
     characters/sliders"

Three separate causes, all fixed here:

1. Slider detection ran BEFORE any tag matching, over the full free-text
   description, with patterns as loose as ``(?:more|less)\\s+\\w+`` and
   ``(?:increase|decrease|boost|reduce|enhance|...)\\s+\\w+``. That is ordinary
   CivitAI marketing copy — "adds more detail", "enhance your images" — so any
   style LoRA describing itself that way was filed as Slider no matter what its
   tags said. Slider now only fires on tags and names, never on the description,
   and only on patterns that actually denote a slider.

2. Matching was plain substring containment, so "person" hit *personality*,
   "pose" hit *purpose* / *composition* / *exposed*, and "detail" hit *detailed*.
   Every keyword is now a word-boundary match.

3. The first keyword hit won outright while iterating a dict whose first entry is
   Character, and name_hints carries the filename — which for a LoRA almost
   always contains a character's name. Categories are now scored, with tags
   outweighing names and names outweighing the description, so an explicit
   ``style`` tag beats an incidental mention anywhere else.
"""

import re

# Keyword sets per category. Deliberately unchanged from the original mapping
# except for Slider: the generic verbs and comparatives that used to live here
# ("more", "less", "boost", "enhance", "adjust", "strength", ...) matched prose,
# not slider LoRAs, and now appear only in _SLIDER_PATTERNS below where they are
# restricted to tags and names.
LORA_CATEGORIES = {
    "Character":  {"character", "celebrity", "person", "people"},
    "Style":      {"style", "art style", "aesthetic"},
    "Clothing":   {"clothing", "fashion", "outfit", "costume", "dress", "shirt"},
    "Concept":    {"concept", "theme", "object", "item", "weapon", "vehicle"},
    "Pose":       {"pose", "action", "stance", "position", "standing", "sitting"},
    "Background": {"background", "environment", "scenery", "landscape", "indoor", "outdoor"},
    "Utility":    {"utility", "tool", "helper", "noise", "offset", "detail"},
    "Slider":     {"slider"},
}

SOURCE_TAG = 'tag'
SOURCE_NAME = 'name'
SOURCE_DESCRIPTION = 'description'

# A tag is curated metadata; a filename is a decent hint; a description is prose
# that happens to contain words. Weighted accordingly.
_SOURCE_WEIGHTS = {SOURCE_TAG: 3, SOURCE_NAME: 2, SOURCE_DESCRIPTION: 1}

CONFIDENCE_HIGH = 'high'
CONFIDENCE_MEDIUM = 'medium'
CONFIDENCE_LOW = 'low'
CONFIDENCE_MANUAL = 'manual'

_CONFIDENCE_BY_SOURCE = {
    SOURCE_TAG: CONFIDENCE_HIGH,
    SOURCE_NAME: CONFIDENCE_MEDIUM,
    SOURCE_DESCRIPTION: CONFIDENCE_LOW,
}

# Ordered weakest to strongest, so a contested match can be demoted one step.
_CONFIDENCE_ORDER = [CONFIDENCE_LOW, CONFIDENCE_MEDIUM, CONFIDENCE_HIGH]

# Strong slider semantics. Applied to tags and names ONLY — running these over a
# free-text description is what produced the false Sliders in the first place.
_SLIDER_PATTERNS = [
    re.compile(r'\bslider\b', re.IGNORECASE),
    re.compile(r'\b(?:adjuster|booster)\b', re.IGNORECASE),
    re.compile(r'\b(?:increase|decrease|intensify|weaken)\s+\w+', re.IGNORECASE),
]

# Descriptions can be several KB of HTML, and this runs once per file across the
# whole library. A LoRA that is about a style says so early; scanning the rest
# only adds cost and stray keyword hits.
_DESCRIPTION_SCAN_LIMIT = 2000

# Sentinel distinguishing "caller said nothing" from a real category.
_AUTO = object()


def _compile(keyword):
    """Word-boundary pattern for a keyword, tolerating any run of whitespace.

    Multi-word keywords such as "art style" must still match "art  style" and
    "art\\nstyle" as they appear in real descriptions.
    """
    body = r'\s+'.join(re.escape(part) for part in keyword.split())
    return re.compile(r'\b' + body + r'\b', re.IGNORECASE)


# Sorted for a deterministic scan order; longer keywords are more specific and
# that length is what breaks score ties below.
_KEYWORD_PATTERNS = {
    category: [(keyword, _compile(keyword)) for keyword in sorted(keywords)]
    for category, keywords in LORA_CATEGORIES.items()
}


def _resolve_manual(manual_category):
    """Interpret the caller's manual_category argument.

    Returns ``_AUTO`` to mean "run the heuristic", or a finished
    ``(category, confidence)`` pair.

    The three states are deliberately distinguishable, which the old sentinel
    could not do: it used the Python object ``None`` for "auto-detection
    disabled" AND as the parameter default AND as the natural return of "no
    sidecar found", so callers that simply omitted the argument silently got
    auto-detection turned off.
    """
    if manual_category is None:
        return _AUTO

    normalized = str(manual_category).strip().lower()
    if normalized in ('', 'auto'):
        return _AUTO
    if normalized == 'none':
        # The user explicitly opted this LoRA out of categorization.
        return None, None
    return manual_category, CONFIDENCE_MANUAL


# Filenames separate words with underscores, hyphens and dots, all of which
# either are word characters or sit between them — so "detail_slider_xl" is a
# single \b-delimited token and no keyword inside it would ever match. Split them
# back into words before scanning.
_NAME_SEPARATORS = re.compile(r'[_\-.]+')


def _iter_sources(tags, description, name_hints):
    """Yield (text, source) for every piece of text worth inspecting."""
    for tag in tags or []:
        if tag:
            yield str(tag), SOURCE_TAG
    for hint in name_hints or []:
        if hint:
            yield _NAME_SEPARATORS.sub(' ', str(hint)), SOURCE_NAME
    if description:
        yield str(description)[:_DESCRIPTION_SCAN_LIMIT], SOURCE_DESCRIPTION


def categorize(tags, manual_category=None, description=None, name_hints=None):
    """Return ``(category, confidence)`` for a LoRA.

    ``manual_category`` accepts the sidecar's stored value: ``None``/``''``/
    ``'Auto'`` run the heuristic, ``'None'`` (the string) disables it, anything
    else is taken as the user's decision and returned as-is.

    ``confidence`` is ``'high'`` when the winning evidence came from a tag,
    ``'medium'`` from a name, ``'low'`` from the description, ``'manual'`` for a
    user-set category, and ``None`` when nothing matched. It is advisory only and
    is never written to disk.
    """
    resolved = _resolve_manual(manual_category)
    if resolved is not _AUTO:
        return resolved

    # category -> [score, best_keyword_length, strongest_source]
    scores = {}

    def _record(category, source, specificity, multiplier=1):
        weight = _SOURCE_WEIGHTS[source] * multiplier
        entry = scores.setdefault(category, [0, 0, SOURCE_DESCRIPTION])
        entry[0] += weight
        entry[1] = max(entry[1], specificity)
        if _SOURCE_WEIGHTS[source] > _SOURCE_WEIGHTS[entry[2]]:
            entry[2] = source

    for text, source in _iter_sources(tags, description, name_hints):
        for category, patterns in _KEYWORD_PATTERNS.items():
            for keyword, pattern in patterns:
                if pattern.search(text):
                    _record(category, source, len(keyword))

        # Slider is the one category with semantics a keyword list cannot carry,
        # and the one most prone to false positives — hence tags/names only.
        if source != SOURCE_DESCRIPTION:
            if any(pattern.search(text) for pattern in _SLIDER_PATTERNS):
                # Weighted above a bare keyword hit from the same source: an
                # explicit "X slider" is a stronger signal than a lone noun.
                _record('Slider', source, len('slider') + 1, multiplier=2)

    if not scores:
        return None, None

    # Highest score wins; ties go to the more specific keyword, then to
    # alphabetical order so the result never depends on dict iteration order.
    ranked = sorted(
        scores.items(),
        key=lambda kv: (-kv[1][0], -kv[1][1], kv[0]),
    )
    category, (score, _specificity, best_source) = ranked[0]
    confidence = _CONFIDENCE_BY_SOURCE[best_source]

    # A runner-up on the same score means the evidence genuinely pointed two
    # ways and the winner was settled by a tie-break, not by the evidence. This
    # is the exact shape of the original complaint — a LoRA tagged both "style"
    # and "character" is a coin flip — so it reports the lowest confidence and
    # sorts to the top of LoraDex's review order rather than passing as certain.
    if len(ranked) > 1 and ranked[1][1][0] == score:
        confidence = CONFIDENCE_LOW

    return category, confidence


def categorize_lora_by_tags(tags, manual_category=None, description=None, name_hints=None):
    """Category-only wrapper, preserving the original call signature."""
    return categorize(tags, manual_category, description, name_hints)[0]
