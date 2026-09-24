"""Test helpers: a real server on a free port with its own throwaway database.

    class MyFeatureTest(AppTestCase):
        def test_something(self):
            status, headers, body = self.get("/things")
            status, headers, body = self.post_form("/things", {"name": "x"})
"""

from __future__ import annotations

import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlencode


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return None


class AppTestCase(unittest.TestCase):
    """Starts the app once per test class against a fresh SQLite file."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls._old_env = {k: os.environ.get(k) for k in ("APP_DATABASE", "APP_QUIET")}
        os.environ["APP_DATABASE"] = str(Path(cls._tmp.name) / "test.sqlite")
        os.environ["APP_QUIET"] = "1"
        from app.server import make_server

        cls.server = make_server("127.0.0.1", 0)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls._thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls._thread.start()
        cls._opener = urllib.request.build_opener(_NoRedirect)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        for key, value in cls._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cls._tmp.cleanup()

    def request(self, method: str, path: str, data: bytes | None = None,
                headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], str]:
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=headers or {})
        try:
            with self._opener.open(req, timeout=10) as resp:
                return resp.status, dict(resp.headers), resp.read().decode("utf-8")
        except urllib.error.HTTPError as err:
            return err.code, dict(err.headers), err.read().decode("utf-8")

    def get(self, path: str) -> tuple[int, dict[str, str], str]:
        return self.request("GET", path)

    def post_form(self, path: str, fields: dict[str, str]) -> tuple[int, dict[str, str], str]:
        return self.request("POST", path, urlencode(fields).encode(),
                            {"Content-Type": "application/x-www-form-urlencoded"})
