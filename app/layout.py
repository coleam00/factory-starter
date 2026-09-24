"""The shared page shell. Every page renders through page() so the app looks
like one product. Escape user data with web.h() before passing it in."""

from __future__ import annotations

import os

from app.web import h

APP_NAME = os.environ.get("APP_NAME", "My App")

NAV: list[tuple[str, str]] = [("/", "Home")]
"""(href, label) pairs shown in the header. Features append their own entry."""


def page(title: str, body: str, flash: str = "") -> str:
    nav = "".join(f'<a href="{h(href)}">{h(label)}</a>' for href, label in NAV)
    notice = f'<p class="flash" role="status">{h(flash)}</p>' if flash else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{h(title)} · {h(APP_NAME)}</title>
<link rel="stylesheet" href="/static/style.css">
</head>
<body>
<header class="top"><span class="brand">{h(APP_NAME)}</span><nav>{nav}</nav></header>
<main>
{notice}
{body}
</main>
</body>
</html>"""
