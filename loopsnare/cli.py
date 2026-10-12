import argparse
import json
import sys

from . import __version__
from .core import analyze, load


def main(argv=None):
    p = argparse.ArgumentParser(prog="loopsnare", description="Detect runaway loops in agent tool-call traces (JSONL).")
    p.add_argument("traces", nargs="+")
    p.add_argument("--repeat", type=int, default=3, help="identical consecutive calls to flag (default 3)")
    p.add_argument("--stall", type=int, default=4, help="same-result calls to flag (default 4)")
    p.add_argument("--cycle-reps", type=int, default=3)
    p.add_argument("--pingpong", type=int, default=6)
    p.add_argument("--json", action="store_true")
    p.add_argument("--fail-on", choices=["none", "medium", "high"], default="high")
    p.add_argument("--version", action="version", version=__version__)
    a = p.parse_args(argv)
    reports, worst = {}, 0
    rank = {"medium": 1, "high": 2}
    for path in a.traces:
        try:
            r = analyze(load(path), a.repeat, a.stall, a.cycle_reps, a.pingpong)
        except (OSError, ValueError) as e:
            print(f"loopsnare: {path}: {e}", file=sys.stderr)
            return 2
        reports[path] = r
        for f in r["findings"]:
            worst = max(worst, rank[f["severity"]])
    if a.json:
        print(json.dumps(reports, indent=2))
    else:
        for path, r in reports.items():
            print(f"{path}: {r['events']} calls, {len(r['findings'])} findings, ~{r['wasted_calls']} wasted calls")
            for f in r["findings"]:
                print(f"  [{f['severity'].upper():6}] {f['kind']:8} lines {f['lines'][0]}-{f['lines'][1]}: {f['message']}")
    if a.fail_on != "none" and worst >= rank[a.fail_on]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
