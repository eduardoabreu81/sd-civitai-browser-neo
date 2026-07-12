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


def _error(message, code=None):
    debug_print(f"[MCP] error: {message} (code={code})")
    return {'ok': False, 'error': str(message), 'code': code}


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
        return _error(text or 'tool reported an error')

    data = result.get('structuredContent')
    if data is None:
        data = text
    return {'ok': True, 'data': data, 'text': text}


# === High-level account/social helpers ======================================

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
