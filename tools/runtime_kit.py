"""Runtime verification kit for apps built on this starter (tools/, never part of the app).

Writes the private files the factory's runtime and holdout verification need, in
the exact shape proven on Windows on 2026-09-24 (standalone runtime host +
--connection-file in every scenario command). Keep the private dir OUTSIDE the app
repo: the builder must never read it.

    python tools/runtime_kit.py init   --app . --private ../private --name "My App"
    python tools/runtime_kit.py assert --private ../private --case baseline --id create-thing \
        --text "From fresh state: create a thing named X ... expect ..."
    python tools/runtime_kit.py assert --private ../private --case holdout --id hostile-input --text "..."
    python tools/runtime_kit.py show   --private ../private

Then, from the app repo, keep the runtime host running in its own terminal:

    python factory/runtime_host.py serve --config <private>/runtime.json --connection-file <private>/connection.json

and pass --input scenario=<private>/baseline.json --input holdout=<private>/holdout.json
to archon-lifecycle.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# The starter's stack contract. Only change these if you changed the starter.
INCLUDE = ["app"]
COMMAND = ["{python}", "-m", "app.server", "--port", "{port}"]
MUTATION = {
    "id": "negative",
    "file": "app/web.py",
    # Breaks form parsing, so every create/edit flow in any app on this starter fails.
    "find": "return {k: v[-1].strip() for k, v in parse_qs(text, keep_blank_values=True).items()}",
    "replace": "return {}",
}

PREAMBLE = (
    "Use `python factory/runtime_host.py describe --slot {slot} --connection-file {cf}` to get the "
    "target URL and source revision; confirm the source revision equals the delivered checkout HEAD "
    "and /build-id equals the described candidate. Drive the app only through its public HTTP "
    "interface (the HTML pages and forms a person would use; discover them from the home page and "
    "navigation). Capture every request's method, URL, status, relevant headers and raw body into "
    "evidence files and read them before judging. Never write the database, seed state, or edit "
    "source or assertions."
)


def posix(p: Path) -> str:
    return p.resolve().as_posix()


def environment(private: Path, slot: str) -> dict[str, str]:
    w, cf = posix(private), posix(private / "connection.json")
    return {
        "ownership": "external",
        "setup": f"python factory/runtime_resource.py prepare --config {w}/runtime.json --destination {w}/candidate",
        "start": f"python factory/runtime_resource.py start --root candidate --slot {slot} --connection-file {cf}",
        "candidate_command": f"python factory/runtime_host.py identity --slot {slot} --connection-file {cf}",
        "teardown": f"python factory/runtime_host.py teardown --slot {slot} --connection-file {cf}",
    }


def cmd_init(args: argparse.Namespace) -> None:
    app, private = Path(args.app), Path(args.private)
    web = app / MUTATION["file"]
    if not web.is_file() or web.read_text(encoding="utf-8").count(MUTATION["find"]) != 1:
        sys.exit(f"{web}: the mutation anchor must appear exactly once (is this app built on factory-starter?)")
    if private.resolve().is_relative_to(app.resolve()):
        sys.exit("the private dir must be outside the app repo")
    private.mkdir(parents=True, exist_ok=True)
    runtime = {
        "version": 1,
        "roots": {"candidate": {"path": posix(private) + "/candidate", "binding": ".factory-resource.json"}},
        "include": INCLUDE,
        "shape": "http",
        "command": COMMAND,
        "env": {"APP_DATABASE": "{state}/app.sqlite", "APP_NAME": args.name, "APP_QUIET": "1"},
        "health_path": "/health",
        "identity_path": "/build-id",
        "timeout_s": 30,
        "mutations": [MUTATION],
    }
    write(private / "runtime.json", runtime)
    for case in ("baseline", "holdout"):
        target = private / f"{case}.json"
        if not target.exists():
            write(target, {"assertions": [], "environment": environment(private, case)})
    print(f"wrote {posix(private)}/runtime.json, baseline.json, holdout.json")


def cmd_assert(args: argparse.Namespace) -> None:
    private = Path(args.private)
    target = private / f"{args.case}.json"
    data = json.loads(target.read_text(encoding="utf-8"))
    pre = PREAMBLE.format(slot=args.case, cf=posix(private / "connection.json"))
    data["assertions"] = [a for a in data["assertions"] if a["id"] != args.id]
    data["assertions"].append({"id": args.id, "description": f"{pre} {args.text.strip()}"})
    write(target, data)
    print(f"{args.case}: {[a['id'] for a in data['assertions']]}")


def cmd_show(args: argparse.Namespace) -> None:
    private = Path(args.private)
    for case in ("baseline", "holdout"):
        data = json.loads((private / f"{case}.json").read_text(encoding="utf-8"))
        print(f"{case}: {[a['id'] for a in data['assertions']] or 'NO ASSERTIONS YET'}")


def write(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init"); p.add_argument("--app", required=True); p.add_argument("--private", required=True)
    p.add_argument("--name", default="My App"); p.set_defaults(func=cmd_init)
    p = sub.add_parser("assert"); p.add_argument("--private", required=True)
    p.add_argument("--case", choices=["baseline", "holdout"], required=True)
    p.add_argument("--id", required=True); p.add_argument("--text", required=True); p.set_defaults(func=cmd_assert)
    p = sub.add_parser("show"); p.add_argument("--private", required=True); p.set_defaults(func=cmd_show)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
