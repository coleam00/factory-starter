# AGENTS.md

A small web app on the Python standard library and SQLite. No third-party
packages, ever: the factory's verification copies the app and runs it with a plain
interpreter, so a dependency makes every check unrunnable.

## Codebase map

| Path | What lives there |
|------|------------------|
| `app/web.py` | Routing (`@route`), `Request`, `Response`, `html_response`, `json_response`, `redirect`, `h()` (HTML escape) |
| `app/server.py` | The server, plus built-in routes: `/`, `/health`, `/build-id`, `/static/{name}` |
| `app/db.py` | `connect()` and named migrations (`db.migration(name, sql)`) |
| `app/layout.py` | `page(title, body)` shell and the `NAV` list |
| `app/features/` | **One module per feature**, auto-imported at startup |
| `app/static/style.css` | Shared styles: `.card`, `.grid`, `table`, `form`, `.badge`, `.flash`, `.error` |
| `tests/support.py` | `AppTestCase`: a real server on a free port with a throwaway database |

## Commands

```bash
python -m app.server --port 8080          # run it (APP_NAME, APP_DATABASE, PORT env vars)
python -m compileall -q app tests         # static check
python -m unittest discover -s tests      # all tests, well under 10 seconds
```

## Where new code goes

A feature is a vertical slice: `app/features/<feature>.py` + `tests/test_<feature>.py`.
Routes, SQL and HTML for that feature stay in that one module.

```python
from app import db
from app.layout import NAV, page
from app.web import Request, Response, h, html_response, redirect, route

db.migration("things_001_create", "CREATE TABLE IF NOT EXISTS things (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
NAV.append(("/things", "Things"))

@route("GET", "/things")
def list_things(req: Request) -> Response:
    conn = db.connect()
    try:
        rows = conn.execute("SELECT id, name FROM things ORDER BY id").fetchall()
    finally:
        conn.close()
    items = "".join(f"<li>{h(r['name'])}</li>" for r in rows)
    return html_response(page("Things", f"<h1>Things</h1><ul>{items}</ul>"))
```

## Ground rules

- **Schema changes are new named migrations.** Register them at the top of the
  feature module with `db.migration("<feature>_<NNN>_<what>", sql)`. Never edit a
  migration that has shipped; add the next one. Load order does not matter.
- **Escape every user value** that reaches HTML with `h()`. No exceptions.
- **Parameterized SQL only** (`?` placeholders). Never format values into SQL.
- **POST forms answer `redirect()` (303)** on success. On a validation error,
  re-render the form with a 400 status and an `.error` message. Never a 500.
- **Every route gets a test** in `tests/test_<feature>.py` using `AppTestCase`.
  Write one test per acceptance criterion AND per branch: happy path, each invalid
  input, unknown id, non-numeric id, and wrong or missing token all get their own
  test. For forms, assert on the rendered HTML (inputs, hidden fields, error text),
  not only on the POST.
- **No copy-paste between routes.** When two routes in a module share logic (an
  authorization check, a write to the same table, a lookup), put it in one private
  helper that every route calls. Security checks especially have exactly one home.
- **`/health` and `/build-id` keep working.** The factory verifies against them.
- Close every connection you open (`try/finally`).
- Keep one concern per change. A feature ticket touches its own module, its own
  test file, and at most `NAV` and its own migrations.
