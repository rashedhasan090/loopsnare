# loopsnare

Catch AI agents stuck in loops by reading their tool-call traces. Stdlib-only Python, no dependencies.

Agents burn tokens and money when they retry the same call, bounce between two tools, keep hitting the same error with new arguments, or hand off back and forth between agents. `loopsnare` reads a JSONL trace (one tool call per line) and flags:

- **repeat**: identical tool + args called N times in a row
- **cycle**: a sequence like `read_file -> write_file` repeating (periods 2-6)
- **stall**: the same tool returning the same result across different args (no progress)
- **pingpong**: two agents alternating turns with nothing else happening

It also estimates how many calls were wasted.

## Demo

```
$ python -m loopsnare examples/trace.jsonl
examples/trace.jsonl: 14 calls, 3 findings, ~7 wasted calls
  [HIGH  ] repeat   lines 1-4: search called 4x in a row with identical args
  [HIGH  ] cycle    lines 5-10: cycle read_file -> write_file repeated 3x
  [MEDIUM] stall    lines 11-14: fetch returned the same result 4x across 4 different args
```

## Trace format

```json
{"agent": "planner", "tool": "search", "args": {"q": "..."}, "result": "..."}
```

`tool` is required; `args`, `result`, `agent` are optional. Lines without `tool` are skipped.

## Options

`--repeat N`, `--stall N`, `--cycle-reps N`, `--pingpong N` tune thresholds. `--json` prints machine-readable output. `--fail-on {none,medium,high}` controls the exit code (default: exit 1 on any high finding) for CI.

## Tests

```
python -m unittest discover -s tests
```

MIT licensed.
