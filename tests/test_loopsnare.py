import json, os, tempfile, unittest
from loopsnare.core import analyze, find_cycles, find_pingpong, find_repeats, find_stalls, load
from loopsnare.cli import main

EX = os.path.join(os.path.dirname(__file__), "..", "examples", "trace.jsonl")


def ev(tool, args=None, result=None, agent=None, n=0):
    e = {"tool": tool, "args": args, "_line": n}
    if result is not None:
        e["result"] = result
    if agent:
        e["agent"] = agent
    return e


def seq(*items):
    return [dict(e, _line=i + 1) for i, e in enumerate(items)]


class T(unittest.TestCase):
    def test_repeat(self):
        f = find_repeats(seq(*[ev("s", {"q": 1})] * 4))
        self.assertEqual(f[0]["count"], 4)

    def test_repeat_below_threshold(self):
        self.assertEqual(find_repeats(seq(ev("s", 1), ev("s", 1))), [])

    def test_diff_args_not_repeat(self):
        self.assertEqual(find_repeats(seq(ev("s", 1), ev("s", 2), ev("s", 3))), [])

    def test_cycle(self):
        f = find_cycles(seq(*[ev("a"), ev("b")] * 3))
        self.assertEqual((f[0]["period"], f[0]["count"]), (2, 3))

    def test_cycle_period3(self):
        f = find_cycles(seq(*[ev("a"), ev("b"), ev("c")] * 3))
        self.assertEqual(f[0]["period"], 3)

    def test_no_cycle(self):
        self.assertEqual(find_cycles(seq(ev("a"), ev("b"), ev("a"), ev("c"))), [])

    def test_stall(self):
        f = find_stalls(seq(*[ev("f", i, "403") for i in range(4)]))
        self.assertEqual(f[0]["count"], 4)

    def test_stall_needs_varied_args(self):
        self.assertEqual(find_stalls(seq(*[ev("f", 1, "403")] * 5)), [])

    def test_pingpong(self):
        f = find_pingpong(seq(*[ev("handoff", i, agent="ab"[i % 2]) for i in range(6)]))
        self.assertEqual(f[0]["agents"], ["a", "b"])

    def test_example(self):
        r = analyze(load(EX))
        kinds = sorted({f["kind"] for f in r["findings"]})
        self.assertEqual(kinds, ["cycle", "repeat", "stall"])
        self.assertGreater(r["wasted_calls"], 0)

    def test_bad_json(self):
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as t:
            t.write("{bad\n")
        with self.assertRaises(ValueError):
            load(t.name)

    def test_cli_exit_codes(self):
        self.assertEqual(main([EX]), 1)
        self.assertEqual(main([EX, "--fail-on", "none"]), 0)

    def test_cli_clean(self):
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as t:
            t.write(json.dumps({"tool": "a", "args": 1}) + "\n")
        self.assertEqual(main([t.name]), 0)


if __name__ == "__main__":
    unittest.main()
