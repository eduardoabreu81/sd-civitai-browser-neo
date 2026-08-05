"""Tests for the CivitAI MCP client envelope and identity extraction.

Context (probed live on 2026-08-05 with a real API key): CivitAI's MCP server is
healthy and authentication works — `list_notifications`, `get_my_resource_review`
and `toggle_favorite_model` all succeed. But every tool whose underlying tRPC
procedure takes NO arguments fails with "Invalid input":

    whoami              -> user.getSelfStatus: Invalid input
    check_notifications -> user.checkNotifications: Invalid input
    list_chats          -> chat.getAllByUser: Invalid input

That is a server-side regression; nothing the client sends can influence it,
since those tools declare an empty `inputSchema`. These tests pin the two
behaviours that keep the failure from reaching the user as a scary banner:
the error envelope must carry any payload that came with the failure, and the
identity extractor must report "no identity" rather than inventing one.
"""

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


MCP_PATH = Path(__file__).resolve().parents[1] / "scripts" / "civitai_mcp.py"


def _load_civitai_mcp_with_stubs():
    modules_pkg = types.ModuleType("modules")
    shared_mod = types.ModuleType("modules.shared")
    shared_mod.opts = types.SimpleNamespace(custom_api_key="test-key")

    global_mod = types.ModuleType("scripts.civitai_global")
    global_mod.print = print
    global_mod.debug_print = lambda *args, **kwargs: None

    overrides = {
        "modules": modules_pkg,
        "modules.shared": shared_mod,
        "scripts.civitai_global": global_mod,
    }

    with patch.dict(sys.modules, overrides, clear=False):
        spec = importlib.util.spec_from_file_location("scripts.civitai_mcp", MCP_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self._payload


class TestCallToolEnvelope(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mcp = _load_civitai_mcp_with_stubs()

    def _call(self, result):
        payload = {"jsonrpc": "2.0", "id": 1, "result": result}
        with patch.object(self.mcp.requests, "post", return_value=_FakeResponse(payload)):
            return self.mcp.call_tool("whoami", {}, authed=True)

    def test_tool_error_keeps_the_structured_payload(self):
        """The real 2026-08-05 whoami failure. `data` must survive onto the error
        envelope so callers can salvage anything the server did resolve."""
        res = self._call({
            "content": [{"type": "text", "text": "Error: user.getSelfStatus: Invalid input"}],
            "structuredContent": {"ok": False, "error": "user.getSelfStatus: Invalid input"},
            "isError": True,
        })
        self.assertFalse(res["ok"])
        self.assertIn("user.getSelfStatus", res["error"])
        self.assertEqual(res["data"], {"ok": False, "error": "user.getSelfStatus: Invalid input"})

    def test_success_returns_structured_content(self):
        res = self._call({
            "content": [{"type": "text", "text": "You are alice"}],
            "structuredContent": {"id": 7, "username": "alice"},
        })
        self.assertTrue(res["ok"])
        self.assertEqual(res["data"], {"id": 7, "username": "alice"})
        self.assertEqual(res["text"], "You are alice")

    def test_jsonrpc_error_has_a_data_key(self):
        """Every error envelope exposes `data`, so callers never KeyError on it."""
        payload = {"jsonrpc": "2.0", "id": 1, "error": {"code": -32602, "message": "nope"}}
        with patch.object(self.mcp.requests, "post", return_value=_FakeResponse(payload)):
            res = self.mcp.call_tool("whoami", {}, authed=True)
        self.assertFalse(res["ok"])
        self.assertIsNone(res["data"])

    def test_missing_api_key_short_circuits(self):
        self.mcp.opts.custom_api_key = ""
        try:
            res = self.mcp.call_tool("whoami", {}, authed=True)
        finally:
            self.mcp.opts.custom_api_key = "test-key"
        self.assertFalse(res["ok"])
        self.assertIn("no API key", res["error"])


class TestExtractIdentity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mcp = _load_civitai_mcp_with_stubs()

    def test_the_real_broken_whoami_payload_yields_nothing(self):
        """What CivitAI actually returns today. Must NOT be mistaken for an
        identity — the badge has to stay hidden rather than render garbage."""
        self.assertEqual(
            self.mcp.extract_identity({"ok": False, "error": "user.getSelfStatus: Invalid input"}),
            (None, None),
        )

    def test_top_level_identity(self):
        self.assertEqual(
            self.mcp.extract_identity({"id": 1, "username": "alice", "image": "http://x/a.png"}),
            ("alice", "http://x/a.png"),
        )

    def test_nested_user_identity(self):
        self.assertEqual(
            self.mcp.extract_identity({"ok": False, "user": {"username": "bob"}}),
            ("bob", None),
        )

    def test_profile_picture_object(self):
        """CivitAI embeds user images as {profilePicture: {url: ...}}."""
        self.assertEqual(
            self.mcp.extract_identity(
                {"username": "carol", "profilePicture": {"url": "abc-123", "nsfwLevel": 2}}
            ),
            ("carol", "abc-123"),
        )

    def test_blank_username_is_not_an_identity(self):
        self.assertEqual(self.mcp.extract_identity({"username": "   "}), (None, None))

    def test_malformed_input(self):
        for bad in (None, [], "alice", 42, {}):
            with self.subTest(bad=bad):
                self.assertEqual(self.mcp.extract_identity(bad), (None, None))


if __name__ == "__main__":
    unittest.main()
