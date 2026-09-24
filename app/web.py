"""A very small web layer on the standard library.

Routes are registered with @route and live next to the feature they belong to
(app/features/<name>.py). A handler takes a Request and returns a Response.
Nothing here needs a third-party package, so the app runs anywhere Python 3.10+ runs.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import parse_qs, urlparse

Handler = Callable[["Request"], "Response"]
_ROUTES: list[tuple[str, re.Pattern[str], Handler]] = []


def route(method: str, pattern: str) -> Callable[[Handler], Handler]:
    """Register a handler. `pattern` is a path with {name} placeholders,
    e.g. "/items/{item_id}". Placeholders match one path segment."""
    regex = "^" + re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", pattern) + "$"

    def register(handler: Handler) -> Handler:
        _ROUTES.append((method.upper(), re.compile(regex), handler))
        return handler

    return register


def resolve(method: str, path: str) -> tuple[Handler | None, dict[str, str], bool]:
    """Find the handler for a request. The third value says whether the path
    exists under another method, so the caller can answer 405 instead of 404."""
    path_known = False
    for m, regex, handler in _ROUTES:
        match = regex.match(path)
        if match:
            path_known = True
            if m == method.upper():
                return handler, match.groupdict(), True
    return None, {}, path_known


@dataclass
class Request:
    method: str
    path: str
    query: dict[str, str]
    headers: dict[str, str]
    body: bytes = b""
    params: dict[str, str] = field(default_factory=dict)

    @classmethod
    def build(cls, method: str, raw_path: str, headers: dict[str, str], body: bytes) -> "Request":
        parsed = urlparse(raw_path)
        query = {k: v[-1] for k, v in parse_qs(parsed.query).items()}
        return cls(method.upper(), parsed.path or "/", query, headers, body)

    @property
    def form(self) -> dict[str, str]:
        """Fields from an application/x-www-form-urlencoded body (last value wins)."""
        text = self.body.decode("utf-8", errors="replace")
        return {k: v[-1].strip() for k, v in parse_qs(text, keep_blank_values=True).items()}

    def json(self) -> object:
        return json.loads(self.body.decode("utf-8") or "null")


@dataclass
class Response:
    status: int = 200
    body: bytes = b""
    headers: dict[str, str] = field(default_factory=dict)


def html_response(markup: str, status: int = 200) -> Response:
    return Response(status, markup.encode("utf-8"), {"Content-Type": "text/html; charset=utf-8"})


def json_response(data: object, status: int = 200) -> Response:
    return Response(
        status,
        json.dumps(data).encode("utf-8"),
        {"Content-Type": "application/json", "Cache-Control": "no-store"},
    )


def text_response(text: str, status: int = 200) -> Response:
    return Response(status, text.encode("utf-8"), {"Content-Type": "text/plain; charset=utf-8"})


def redirect(location: str, status: int = 303) -> Response:
    """303 after a form POST, so a refresh never re-submits."""
    return Response(status, b"", {"Location": location})


def h(value: object) -> str:
    """Escape anything user-supplied before it goes into HTML. Always."""
    return html.escape("" if value is None else str(value), quote=True)
