"""The HTTP server and the app's built-in routes (/, /health, /build-id, /static).

Run it:  python -m app.server --port 8080
Features live in app/features/ and are imported automatically at startup.
"""

from __future__ import annotations

import argparse
import importlib
import mimetypes
import os
import pkgutil
import subprocess
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from app import db, features
from app.layout import APP_NAME, page
from app.web import Request, Response, html_response, json_response, resolve, route, text_response

HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"


def build_id() -> str:
    """What this running process was built from, so a verifier can tell it apart
    from a stale copy. The runtime host's candidate identity wins, then an explicit
    APP_BUILD_ID, then the checked-out commit."""
    for key in ("FACTORY_RUNTIME_CANDIDATE", "APP_BUILD_ID"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=HERE.parent, capture_output=True,
            text=True, timeout=5, check=True,
        ).stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


@route("GET", "/health")
def health(_req: Request) -> Response:
    conn = db.connect()
    try:
        conn.execute("SELECT 1").fetchone()
    finally:
        conn.close()
    return json_response({"status": "ok"})


@route("GET", "/build-id")
def build_identity(_req: Request) -> Response:
    return text_response(build_id())


@route("GET", "/")
def home(_req: Request) -> Response:
    body = f"""<section class="hero">
<h1>{APP_NAME}</h1>
<p>This app is built by an AI software factory. Every feature arrives as a reviewed,
verified pull request.</p>
</section>"""
    return html_response(page("Home", body))


@route("GET", "/static/{name}")
def static_file(req: Request) -> Response:
    target = (STATIC / req.params["name"]).resolve()
    if STATIC.resolve() not in target.parents or not target.is_file():
        return text_response("not found", 404)
    ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    return Response(200, target.read_bytes(), {"Content-Type": ctype})


def load_features() -> None:
    """Import every module in app/features so its @route handlers register."""
    for info in pkgutil.iter_modules(features.__path__):
        importlib.import_module(f"app.features.{info.name}")


class Handler(BaseHTTPRequestHandler):
    server_version = "starter"

    def _dispatch(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        req = Request.build(self.command, self.path, dict(self.headers), body)
        handler, params, path_known = resolve(req.method, req.path)
        if handler is None:
            resp = text_response("method not allowed", 405) if path_known else html_response(
                page("Not found", "<h1>Not found</h1>"), 404)
        else:
            req.params = params
            try:
                resp = handler(req)
            except Exception:  # noqa: BLE001 - a crash must answer 500, never hang
                traceback.print_exc()
                resp = text_response("internal error", 500)
        self.send_response(resp.status)
        for key, value in resp.headers.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(resp.body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(resp.body)

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = _dispatch

    def log_message(self, fmt: str, *args: object) -> None:
        if os.environ.get("APP_QUIET"):
            return
        super().log_message(fmt, *args)


def make_server(host: str = "127.0.0.1", port: int = 8080) -> ThreadingHTTPServer:
    load_features()
    db.connect().close()  # create and migrate the database before the first request
    return ThreadingHTTPServer((host, port), Handler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the app")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8080")))
    args = parser.parse_args()
    server = make_server(args.host, args.port)
    print(f"{APP_NAME} listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
