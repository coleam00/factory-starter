"""PreToolUse guard: no coding agent may merge a pull request.

In the AI software factory the ONLY thing allowed to merge is the merge queue's
deterministic script (it calls gh itself, not through an agent tool), and only
after runtime, holdout and qualification pass. On 2026-09-24 an agent node merged
its own PR before verification in 2 of 3 laps. A prompt asking it not to is a
request; this is a guarantee. Exit 2 blocks the tool call and tells the agent why.
"""

import json
import re
import sys
from pathlib import Path

MERGE = re.compile(
    r"\bgh\s+pr\s+merge\b"                      # gh pr merge ...
    r"|\bgh\s+api\b[^|;&]*?/pulls/\d+/merge\b"  # gh api -X PUT repos/o/r/pulls/N/merge
    r"|\bgh\s+pr\s+review\b[^|;&]*--approve"    # self-approval to satisfy protection
)

try:
    event = json.load(sys.stdin)
except Exception:
    sys.exit(0)

command = str((event.get("tool_input") or {}).get("command") or "")
if event.get("tool_name") == "Bash" and MERGE.search(command):
    try:  # evidence for the operator, kept OUTSIDE the checkout so it never dirties it
        with open(Path.home() / ".factory-merge-block.log", "a", encoding="utf-8") as log:
            log.write(json.dumps({"cwd": event.get("cwd"), "command": command[:300]}) + "\n")
    except OSError:
        pass
    print("Blocked: agents never merge or approve PRs in this factory. The merge queue's "
          "script merges after runtime, holdout and qualification pass. Report your result "
          "and stop.", file=sys.stderr)
    sys.exit(2)
sys.exit(0)
