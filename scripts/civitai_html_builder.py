"""Pure HTML builder functions for CivitAI Browser Neo model detail overlay.

This module contains no API calls, no filesystem logic, and no global state.
Each function takes primitive data and returns an HTML string.
"""

import os
import re
from html import escape


def build_tags_html(tags):
    """Join tags into inline <span class="civitai-tag"> HTML."""
    return ''.join([f'<span class="civitai-tag">{escape(str(tag))}</span>' for tag in tags])


def build_permissions_html(item):
    """Build permissions <p> block with allow/deny SVG icons."""
    allow_svg = '<svg width="16" height="16" viewBox="0 1.5 24 24" stroke-width="4" stroke-linecap="round" stroke="lime"><path d="M5 12l5 5l10 -10"></path></svg>'
    deny_svg = '<svg width="16" height="16" viewBox="0 1.5 24 24" stroke-width="4" stroke-linecap="round" stroke="red"><path d="M18 6l-12 12"></path><path d="M6 6l12 12"></path></svg>'
    allowCommercialUse = item.get('allowCommercialUse', [])

    return (
        '<p>'
            f'{allow_svg if item.get("allowNoCredit") else deny_svg} Use the model without crediting the creator<br/>'
            f'{allow_svg if "Image" in allowCommercialUse else deny_svg} Sell images they generate<br/>'
            f'{allow_svg if "Rent" in allowCommercialUse else deny_svg} Run on services that generate images for money<br/>'
            f'{allow_svg if "RentCivit" in allowCommercialUse else deny_svg} Run on Civitai<br/>'
            f'{allow_svg if item.get("allowDerivatives") else deny_svg} Share merges using this model<br/>'
            f'{allow_svg if "Sell" in allowCommercialUse else deny_svg} Sell this model or merges using this model<br/>'
            f'{allow_svg if item.get("allowDifferentLicense") else deny_svg} Have different permissions when sharing merges'
        '</p>'
    )


def build_model_page_html(model_name, model_main_url, selected_version_id, is_local_only):
    """Build .model-page-line header block."""
    if is_local_only:
        return (
            '<div class="model-page-line">'
                '<span class="page-label">Model Source:</span>'
                f'<span>{escape(str(model_name))} (Local file only)</span>'
            '</div>'
        )
    return (
        '<div class="model-page-line">'
            '<span class="page-label">Model Page:</span>'
            f'<a href={model_main_url}?modelVersionId={selected_version_id} target="_blank">{escape(str(model_name))}</a>'
        '</div>'
    )


def build_uploader_html(model_uploader, uploader_avatar, creator):
    """Build .model-uploader-line block with avatar."""
    if not creator or model_uploader == 'User not found':
        return (
            '<div class="model-uploader-line">'
                '<span class="uploader-label">Uploaded Unknown:</span>'
                f'<span>{escape(str(model_uploader))}</span>'
                f'{uploader_avatar}'
            '</div>'
        )
    return (
        '<div class="model-uploader-line">'
            '<span class="uploader-label">Uploaded by:</span>'
            f'<a href="https://civitai.com/user/{escape(str(model_uploader))}" target="_blank">{escape(str(model_uploader))}</a>'
            f'{uploader_avatar}'
        '</div>'
    )


def build_version_info_html(
    display_type,
    model_version,
    output_basemodel,
    model_availability,
    model_date_published,
    tags_html,
    sha256_value,
    model_url,
):
    """Build .version-info-block <dl> with model metadata."""
    _sha256_row = (
        f'<dt>SHA256</dt>'
        f'<dd><span style="font-family:monospace;font-size:11px;word-break:break-all;user-select:all;">{escape(sha256_value)}</span></dd>'
    ) if sha256_value and sha256_value != 'Unknown' else ''

    return (
        '<div class="version-info-block">'
            '<h3 class="block-header">Version Information</h3>'
            '<dl>'
                '<dt>Type</dt>'
                f'<dd>{display_type}</dd>'
                '<dt>Version</dt>'
                f'<dd>{escape(str(model_version))}</dd>'
                '<dt>Base model</dt>'
                f'<dd>{escape(str(output_basemodel))}</dd>'
                '<dt>Availability</dt>'
                f'<dd>{model_availability}</dd>'
                '<dt>Published</dt>'
                f'<dd>{model_date_published}</dd>'
                '<dt>CivitAI tags</dt>'
                '<dd>'
                    '<div class="civitai-tags-container">'
                        f'{tags_html}'
                    '</div>'
                '</dd>'
                f'{_sha256_row}'
                f'{"<dt>Download link</dt>" if model_url else ""}'
                f'{f"<dd><a href={model_url} target=_blank>{model_url}</a></dd>" if model_url else ""}'
            '</dl>'
        '</div>'
    )


def build_version_permissions_html(perms_html):
    """Wrap perms_html in .permissions-block container."""
    return (
        '<div class="permissions-block">'
            '<h3 class="block-header">Permissions</h3>'
            f'{perms_html}'
        '</div>'
    )


def build_description_html(model_desc, from_preview):
    """Build .description-block with toggle overlay and REVIEW_BLOCK_ANCHOR."""
    prefix = "preview-" if from_preview else ""
    return (
        '<div class="description-block">'
            '<h2 class="block-header">Model Description</h2>'
            '<div class="description-wrapper">'
                f'<div class="description-content" id="{prefix}description-content">'
                    f'{model_desc}'
                '</div>'
                f'<div class="description-overlay" id="{prefix}description-overlay"></div>'
                f'<button class="description-toggle-btn" id="{prefix}description-toggle-btn" onclick="toggleDescription(\'{prefix}\')">Show More</button>'
            '</div>'
            '<!-- REVIEW_BLOCK_ANCHOR -->'
        '</div>'
    )


def build_trigger_words_html(raw_trained_words, is_LORA, model_filename):
    """Build .trained-words-block or return empty string."""
    def _sanitize_tw(s):
        s = re.sub(r'<[^>]*:[^>]*>', '', s)
        s = re.sub(r', ?', ', ', s)
        return s.strip(', ')

    sanitized_groups = [_sanitize_tw(g) for g in raw_trained_words if g and _sanitize_tw(g)]

    if not sanitized_groups and not is_LORA:
        return ''

    rows_html = ''
    all_onclick_parts = []

    if is_LORA and model_filename:
        lora_stem = os.path.splitext(model_filename)[0]
        safe_stem_js = lora_stem.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace("'", '&#39;')
        lora_tag_display = f'&lt;lora:{escape(lora_stem)}:1&gt;'
        lora_tag_onclick = f'&lt;lora:{safe_stem_js}:1&gt;'
        rows_html += (
            f'<div class="trigger-word-row lora-tag-row">'
                f'<div class="trigger-word-actions">'
                    f'<button class="tw-copy-btn" onclick="copyTriggerWord(\'{lora_tag_onclick}\', this)" title="Copy">📋</button>'
                    f'<button class="tw-add-btn" onclick="sendTagsToPrompt(\'{lora_tag_onclick}\')" title="Add to prompt">➕</button>'
                f'</div>'
                f'<span class="trigger-word-text">{lora_tag_display}</span>'
            f'</div>'
        )
        all_onclick_parts.append(lora_tag_onclick)

    for group in sanitized_groups:
        safe_group = escape(group).replace("'", '&#39;')
        rows_html += (
            f'<div class="trigger-word-row">'
                f'<div class="trigger-word-actions">'
                    f'<button class="tw-copy-btn" onclick="copyTriggerWord(\'{safe_group}\', this)" title="Copy">📋</button>'
                    f'<button class="tw-add-btn" onclick="sendTagsToPrompt(\'{safe_group}\')" title="Add to prompt">➕</button>'
                f'</div>'
                f'<span class="trigger-word-text">{escape(group)}</span>'
            f'</div>'
        )
        all_onclick_parts.append(safe_group)

    all_onclick = ', '.join(all_onclick_parts)
    add_all_label = '➕ Add all to prompt' if len(all_onclick_parts) > 1 else '➕ Add to prompt'
    return (
        '<div class="trained-words-block">'
            '<h3 class="block-header">Trigger Words</h3>'
            f'{rows_html}'
            f'<button class="add-to-prompt-btn" onclick="sendTagsToPrompt(\'{all_onclick}\')">{add_all_label}</button>'
        '</div>'
    )


def assemble_model_info_html(
    model_page,
    uploader_page,
    version_info,
    version_permissions,
    companion_banner,
    trained_words_section,
    description_section,
    img_html,
):
    """Combine all blocks into final .main-container output_html (legacy layout)."""
    return (
        '<div class="main-container">'
            '<div class="info-section">'
                '<div class="header-block">'
                    f'{model_page}'
                    '<div class="uploader-divider"></div>'
                    f'{uploader_page}'
                '</div>'
                '<div class="info-permissions-container">'
                    f'{version_info}'
                    f'{version_permissions}'
                '</div>'
                f'{companion_banner}'
                f'{trained_words_section}'
                f'{description_section}'
            '</div>'
            '<div class="images-section">'
                f'{img_html}'
            '</div>'
        '</div>'
    )


def build_model_badges_html(display_type, base_model, nsfw_level=None, download_count=None, thumbs_up_count=None):
    """Build header badges row for revamp layout.

    All badge values are optional. If None, the badge is omitted.
    """
    badges = []
    if display_type:
        badges.append(f'<span class="badge badge-type">{escape(str(display_type))}</span>')
    if base_model:
        badges.append(f'<span class="badge badge-base-model">{escape(str(base_model))}</span>')
    if nsfw_level is not None and nsfw_level > 0:
        badges.append(f'<span class="badge badge-nsfw" data-level="{nsfw_level}">NSFW</span>')
    if thumbs_up_count is not None:
        badges.append(f'<span class="badge badge-likes">★ {thumbs_up_count}</span>')
    if download_count is not None:
        badges.append(f'<span class="badge badge-downloads">↓ {download_count}</span>')

    if not badges:
        return ''
    return '<div class="model-meta-badges">' + ''.join(badges) + '</div>'


def build_download_info_card(model_filename, file_meta=None):
    """Build download info card for revamp sidebar.

    file_meta: human-readable string like 'SafeTensor · fp16 · 6.46 GB'.
    """
    if not model_filename:
        return ''
    meta_line = f'<span class="file-meta">{escape(str(file_meta))}</span>' if file_meta else ''
    return (
        '<div class="card card-download">'
            '<h3 class="card-header">File</h3>'
            f'<div class="file-name">{escape(str(model_filename))}</div>'
            f'{meta_line}'
        '</div>'
    )


def build_local_model_status_card():
    """Build Local Model Status card for revamp sidebar.

    The review block anchor is placed inside this card so that
    _inject_review_block_into_model_html can inject the review UI here.
    """
    return (
        '<div class="card card-local-status">'
            '<h3 class="card-header">Local Model Status</h3>'
            '<!-- REVIEW_BLOCK_ANCHOR -->'
        '</div>'
    )


def assemble_model_info_html_revamp(
    model_page,
    uploader_page,
    model_badges_html,
    description_section,
    img_html,
    download_info_card,
    trained_words_section,
    local_status_card,
    metadata_card,
    permissions_card,
    companion_banner,
):
    """Combine all blocks into final two-column revamp layout.

    Sidebar order (top to bottom):
      1. Download info card
      2. Trigger Words (if non-empty and type is LoRA/LoCon/DoRA)
      3. Local Model Status
      4. Metadata
      5. Permissions
      6. Companion Banner (if non-empty)

    The legacy assemble_model_info_html is left untouched.
    """
    # Header area
    header_badges = model_badges_html if model_badges_html else ''
    header = (
        '<div class="revamp-header">'
            f'{model_page}'
            f'{header_badges}'
            f'{uploader_page}'
        '</div>'
    )

    # Primary column: Description + Gallery
    primary = (
        '<div class="primary-column">'
            f'{description_section}'
            f'{img_html}'
        '</div>'
    )

    # Sidebar cards — order is fixed and validated by tests
    sidebar_parts = [download_info_card] if download_info_card else []

    # Trigger Words: only include if there is actual content.
    # Callers must pass an empty string for Checkpoint or when no triggers exist.
    if trained_words_section:
        sidebar_parts.append(trained_words_section)

    sidebar_parts.append(local_status_card)
    sidebar_parts.append(metadata_card)
    sidebar_parts.append(permissions_card)

    if companion_banner:
        sidebar_parts.append(companion_banner)

    sidebar = (
        '<div class="sidebar-column">'
            + ''.join(sidebar_parts)
        + '</div>'
    )

    return (
        '<div class="main-container revamp-layout">'
            f'{header}'
            '<div class="revamp-body">'
                f'{primary}'
                f'{sidebar}'
            '</div>'
        '</div>'
    )
