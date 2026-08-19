"""CivitAI MCP client — account/social features not exposed by the public REST v1 API.

The CivitAI MCP server (https://mcp.civitai.com/mcp) speaks JSON-RPC 2.0 over
streamable HTTP. Probing established three facts that keep this client tiny:

  * Stateless — no ``initialize`` handshake or ``Mcp-Session-Id`` is required;
    a bare ``tools/call`` returns 200.
  * A browser-like ``User-Agent`` is mandatory (Cloudflare returns 1010 without it).
  * Responses are plain ``application/json`` (never SSE) with the envelope
    ``result.content[].text`` (human) + ``result.structuredContent`` (machine);
    failures arrive as a JSON-RPC ``error`` object.

Browse tools (search_models, get_model, ...) need no auth. Account/social tools
(whoami, toggle_follow_user, ...) require a Bearer API key (``opts.custom_api_key``)
from an onboarded account.

Every public function returns a result envelope so callers never see exceptions:
    {'ok': True,  'data': <structuredContent or text>, 'text': <human text>}
    {'ok': False, 'error': <message>, 'code': <jsonrpc code or http status>}
"""

import json
import itertools

import requests

from modules.shared import opts
from scripts.civitai_global import print, debug_print

# Fixed endpoint. CivitAI's MCP lives on its own host, independent of any
# custom REST proxy the user may have configured for the browse API.
MCP_URL = 'https://mcp.civitai.com/mcp'

# Cloudflare blocks requests without a browser-like signature (Error 1010).
_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
)

# Connect/read timeouts mirror civitai_api.request_civit_api.
_TIMEOUT = (60, 30)

_id_counter = itertools.count(1)


def _get_api_key():
    return (getattr(opts, 'custom_api_key', '') or '').strip()


def _get_proxies():
    """Mirror civitai_api.get_proxies without importing it (avoids a cycle)."""
    custom_proxy = getattr(opts, 'custom_civitai_proxy', '')
    disable_ssl = getattr(opts, 'disable_sll_proxy', False)
    cabundle_path = getattr(opts, 'cabundle_path_proxy', '')

    import os
    ssl = True
    proxies = {}
    if custom_proxy:
        if not disable_ssl:
            if cabundle_path:
                ssl = os.path.exists(cabundle_path)
        else:
            ssl = False
        proxies = {'http': custom_proxy, 'https': custom_proxy}
    return proxies, ssl


def _headers(authed):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream',
        'User-Agent': _USER_AGENT,
    }
    if authed:
        key = _get_api_key()
        if key:
            headers['Authorization'] = f'Bearer {key}'
    return headers


def _error(message, code=None, data=None):
    """Error envelope. ``data`` carries any payload the server returned ALONGSIDE
    the failure — a tool can resolve part of its work and still fail on a later
    step, and throwing that away costs callers information they could use."""
    debug_print(f"[MCP] error: {message} (code={code})")
    return {'ok': False, 'error': str(message), 'code': code, 'data': data}


def _mcp_post(method, params, authed):
    """Single JSON-RPC POST. Returns {'ok': True, 'result': ...} or an error envelope."""
    payload = {
        'jsonrpc': '2.0',
        'id': next(_id_counter),
        'method': method,
        'params': params or {},
    }
    proxies, ssl = _get_proxies()
    try:
        resp = requests.post(
            MCP_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers=_headers(authed),
            timeout=_TIMEOUT,
            proxies=proxies,
            verify=ssl,
        )
    except requests.exceptions.RequestException as e:
        return _error(f"network error: {e}")

    if resp.status_code != 200:
        snippet = (resp.text or '')[:200]
        return _error(f"HTTP {resp.status_code}: {snippet}", code=resp.status_code)

    try:
        body = resp.json()
    except ValueError:
        return _error(f"non-JSON response: {(resp.text or '')[:200]}")

    if isinstance(body, dict) and body.get('error'):
        err = body['error']
        return _error(err.get('message', 'unknown JSON-RPC error'), code=err.get('code'))

    result = body.get('result') if isinstance(body, dict) else None
    if result is None:
        return _error(f"missing result in response: {str(body)[:200]}")
    return {'ok': True, 'result': result}


def call_tool(name, arguments=None, authed=True):
    """Invoke an MCP tool. Returns {'ok', 'data', 'text'} or {'ok': False, 'error'}.

    ``data`` is ``structuredContent`` when present, else the concatenated text
    content. ``text`` is always the human-readable text (may be '').
    """
    if authed and not _get_api_key():
        return _error('no API key configured (Settings -> CivitAI API key)')

    res = _mcp_post('tools/call', {'name': name, 'arguments': arguments or {}}, authed)
    if not res['ok']:
        return res

    result = res['result']
    # A tool can report a domain error via isError + content text.
    text_parts = [
        c.get('text', '')
        for c in result.get('content', [])
        if isinstance(c, dict) and c.get('type') == 'text'
    ]
    text = '\n'.join(p for p in text_parts if p)

    if result.get('isError'):
        # Pass structuredContent through: CivitAI's `whoami` resolves the account
        # first and only then calls user.getSelfStatus, so a failure in that second
        # step can still arrive with the identity attached.
        return _error(text or 'tool reported an error', data=result.get('structuredContent'))

    data = result.get('structuredContent')
    if data is None:
        data = text
    return {'ok': True, 'data': data, 'text': text}


# === High-level account/social helpers ======================================

def extract_identity(payload):
    """Dig a ``(username, avatar_url)`` pair out of a whoami payload.

    Returns ``(None, None)`` when the payload carries no usable identity — which
    is the current reality: CivitAI's `whoami` fails in `user.getSelfStatus` and
    answers a bare ``{'ok': False, 'error': ...}`` with no account data at all.
    The tolerance below (top level or nested under ``user``) exists because a
    SUCCESSFUL whoami shape has never been observed here, so this must not assume
    one exact layout. ``profilePicture: {url: ...}`` is not a guess — CivitAI uses
    that shape for user objects embedded in notification payloads.
    """
    if not isinstance(payload, dict):
        return None, None

    sources = [payload]
    nested = payload.get('user')
    if isinstance(nested, dict):
        sources.append(nested)

    for source in sources:
        username = source.get('username') or source.get('name')
        if not isinstance(username, str) or not username.strip():
            continue
        image = source.get('image') or source.get('avatar') or source.get('profilePicture')
        if isinstance(image, dict):
            image = image.get('url')
        return username.strip(), image if isinstance(image, str) and image else None

    return None, None


_whoami_cache = {}


def whoami(use_cache=True):
    """Resolve the current account from the API key (cached per key).

    Called in the background on UI load to render the account badge, so the
    result is memoized per API key to avoid re-hitting the server on every
    page load. Pass use_cache=False to force a refresh.
    """
    key = _get_api_key()
    if use_cache and key and key in _whoami_cache:
        return _whoami_cache[key]
    res = call_tool('whoami', {}, authed=True)
    if key and res.get('ok'):
        _whoami_cache[key] = res
    return res


def toggle_follow_user(user):
    """Toggle following a creator (numeric id or username)."""
    return call_tool('toggle_follow_user', {'user': user}, authed=True)


def check_notifications():
    """Return the unread notification count for the badge."""
    return call_tool('check_notifications', {}, authed=True)
