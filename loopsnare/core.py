"""Loop detection over agent tool-call traces (JSONL, one event per line).

Event fields: tool (str), args (any JSON), result (any, optional), agent (optional).
"""
import hashlib
import json


def _h(obj):
    return hashlib.sha1(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:10]


def load(path):
    events = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"line {n}: invalid JSON: {e}")
            if "tool" not in ev:
                continue
            ev["_line"] = n
            events.append(ev)
    return events


def _sig(ev):
    return (ev.get("tool"), _h(ev.get("args")))


def find_repeats(events, threshold=3):
    """Identical tool+args called consecutively >= threshold times."""
    out, i = [], 0
    while i < len(events):
        j = i
        while j + 1 < len(events) and _sig(events[j + 1]) == _sig(events[i]):
            j += 1
        run = j - i + 1
        if run >= threshold:
            out.append({"kind": "repeat", "severity": "high", "tool": events[i]["tool"],
                        "count": run, "lines": [events[i]["_line"], events[j]["_line"]],
                        "message": f"{events[i]['tool']} called {run}x in a row with identical args"})
        i = j + 1
    return out


def find_cycles(events, min_period=2, max_period=6, min_reps=3):
    """Repeating sequence of tool signatures (A,B,A,B,A,B...)."""
    sigs = [_sig(e) for e in events]
    out, i = [], 0
    while i < len(sigs):
        best = None
        for p in range(min_period, max_period + 1):
            if len(set(sigs[i:i + p])) < 2:
                continue
            reps = 1
            while sigs[i + reps * p:i + (reps + 1) * p] == sigs[i:i + p]:
                reps += 1
            if reps >= min_reps and (best is None or reps * p > best[0] * best[1]):
                best = (reps, p)
        if best:
            reps, p = best
            end = i + reps * p - 1
            tools = [s[0] for s in sigs[i:i + p]]
            out.append({"kind": "cycle", "severity": "high", "period": p, "count": reps,
                        "tools": tools, "lines": [events[i]["_line"], events[end]["_line"]],
                        "message": f"cycle {' -> '.join(tools)} repeated {reps}x"})
            i = end + 1
        else:
            i += 1
    return out


def find_stalls(events, threshold=4):
    """Same tool returns the same result repeatedly despite varying args (no progress)."""
    out, i = [], 0
    while i < len(events):
        if "result" not in events[i]:
            i += 1
            continue
        key = (events[i]["tool"], _h(events[i]["result"]))
        j, argsets = i, {_h(events[i].get("args"))}
        while j + 1 < len(events) and "result" in events[j + 1] and \
                (events[j + 1]["tool"], _h(events[j + 1]["result"])) == key:
            j += 1
            argsets.add(_h(events[j].get("args")))
        run = j - i + 1
        if run >= threshold and len(argsets) > 1:
            out.append({"kind": "stall", "severity": "medium", "tool": key[0], "count": run,
                        "lines": [events[i]["_line"], events[j]["_line"]],
                        "message": f"{key[0]} returned the same result {run}x across {len(argsets)} different args"})
        i = j + 1
    return out


def find_pingpong(events, threshold=6):
    """Two agents handing off back and forth with no other activity."""
    out, i = [], 0
    ag = [e.get("agent") for e in events]
    while i < len(ag) - 1:
        a, b = ag[i], ag[i + 1]
        if not a or not b or a == b:
            i += 1
            continue
        j = i + 1
        while j + 1 < len(ag) and ag[j + 1] == ag[j - 1]:
            j += 1
        run = j - i + 1
        if run >= threshold:
            out.append({"kind": "pingpong", "severity": "medium", "agents": [a, b], "count": run,
                        "lines": [events[i]["_line"], events[j]["_line"]],
                        "message": f"agents {a} <-> {b} alternated {run} turns"})
            i = j + 1
        else:
            i += 1
    return out


def analyze(events, repeat=3, stall=4, cycle_reps=3, pingpong=6):
    findings = (find_repeats(events, repeat) + find_cycles(events, min_reps=cycle_reps)
                + find_stalls(events, stall) + find_pingpong(events, pingpong))
    findings.sort(key=lambda f: f["lines"][0])
    wasted = sum(f["count"] - 1 for f in findings if f["kind"] == "repeat") + \
        sum((f["count"] - 1) * f["period"] for f in findings if f["kind"] == "cycle")
    return {"events": len(events), "findings": findings, "wasted_calls": wasted}
