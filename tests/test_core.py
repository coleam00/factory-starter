import os
import socket
import sqlite3
import unittest
from urllib.parse import urlparse

from app import db
from tests.support import AppTestCase


class CoreRoutesTest(AppTestCase):
    def test_health_reports_ok(self):
        status, headers, body = self.get("/health")
        self.assertEqual(status, 200)
        self.assertIn('"ok"', body)
        self.assertEqual(headers.get("Cache-Control"), "no-store")

    def test_build_id_prefers_runtime_candidate(self):
        os.environ["FACTORY_RUNTIME_CANDIDATE"] = "cand-123"
        try:
            status, _, body = self.get("/build-id")
        finally:
            del os.environ["FACTORY_RUNTIME_CANDIDATE"]
        self.assertEqual(status, 200)
        self.assertEqual(body, "cand-123")

    def test_home_renders_the_shell(self):
        status, headers, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("Content-Type", ""))
        self.assertIn('<link rel="stylesheet" href="/static/style.css">', body)

    def test_unknown_path_is_404_and_wrong_method_is_405(self):
        self.assertEqual(self.get("/nope")[0], 404)
        self.assertEqual(self.request("POST", "/health", b"")[0], 405)

    def test_static_cannot_escape_its_folder(self):
        self.assertEqual(self.get("/static/style.css")[0], 200)
        self.assertEqual(self.get("/static/..%2Fserver.py")[0], 404)


    def raw(self, request: bytes) -> bytes:
        """Send bytes no well-behaved client would, and return whatever comes back."""
        url = urlparse(self.base)
        with socket.create_connection((url.hostname, url.port), timeout=5) as conn:
            conn.sendall(request)
            chunks = []
            while chunk := conn.recv(4096):
                chunks.append(chunk)
        return b"".join(chunks)

    def test_a_malformed_content_length_is_answered_400(self):
        for value in (b"abc", b"-5"):
            head = [b"POST /health HTTP/1.1", b"Host: x", b"Content-Length: " + value,
                    b"Connection: close", b"", b""]
            reply = self.raw(bytes([13, 10]).join(head))
            self.assertTrue(reply.startswith(b"HTTP/1.0 400") or reply.startswith(b"HTTP/1.1 400"),
                            (value, reply[:80]))
        # The server keeps answering afterwards.
        self.assertEqual(self.get("/health")[0], 200)

class MigrationTest(unittest.TestCase):
    def test_migrations_apply_once_by_name(self):
        conn = sqlite3.connect(":memory:")
        first = db.migrate(conn)
        second = db.migrate(conn)
        self.assertEqual(set(first), set(db.MIGRATIONS))
        self.assertEqual(second, [])

    def test_a_late_migration_applies_to_an_existing_database(self):
        conn = sqlite3.connect(":memory:")
        db.migrate(conn)
        db.migration("zz_test_001", "CREATE TABLE zz_test (id INTEGER)")
        try:
            self.assertEqual(db.migrate(conn), ["zz_test_001"])
        finally:
            del db.MIGRATIONS["zz_test_001"]

    def test_reusing_a_name_with_different_sql_fails(self):
        with self.assertRaises(ValueError):
            db.migration("core_001_app_meta", "CREATE TABLE other (id INTEGER)")


if __name__ == "__main__":
    unittest.main()
