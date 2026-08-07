#!/usr/bin/env python3
"""Regression tests for token-meter delta accounting."""

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def load_meter():
    spec = importlib.util.spec_from_file_location(
        "codex_token_meter_write", SCRIPTS / "codex-token-meter-write.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["codex_token_meter_write"] = mod
    spec.loader.exec_module(mod)
    return mod


def write_transcript(path: Path) -> None:
    rows = [
        {
            "id": "turn-1",
            "session_id": "s1",
            "role": "assistant",
            "message": {
                "role": "assistant",
                "model": "gpt-4o-mini",
                "usage": {"input_tokens": 1000, "output_tokens": 100},
            },
        },
        {
            "id": "turn-2",
            "session_id": "s1",
            "role": "assistant",
            "message": {
                "role": "assistant",
                "model": "gpt-4o-mini",
                "usage": {"input_tokens": 2000, "output_tokens": 200},
            },
        },
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")


def write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")


class TokenMeterDeltaCase(unittest.TestCase):
    def setUp(self):
        self.old = os.getcwd()
        self.tmp = tempfile.mkdtemp()
        os.chdir(self.tmp)
        self.meter = load_meter()

    def tearDown(self):
        os.chdir(self.old)

    def test_delta_checkpoint_prevents_duplicate_cost_rows(self):
        transcript = Path("session.jsonl")
        write_transcript(transcript)

        events = self.meter.parse_transcript(str(transcript), "s1")
        delta, checkpoint = self.meter.apply_delta(events, "s1")
        self.assertEqual(len(delta), 2)
        self.meter.append_cost_log(delta, self.meter.checkpoint_session(checkpoint, "s1"))
        self.meter.write_json(self.meter.CHECKPOINT_FILE, checkpoint)

        delta_again, checkpoint_again = self.meter.apply_delta(events, "s1")
        self.assertEqual(delta_again, [])
        self.meter.append_cost_log(delta_again, self.meter.checkpoint_session(checkpoint_again, "s1"))

        rows = Path(".raven/cost-log.jsonl").read_text().splitlines()
        self.assertEqual(len(rows), 2)
        metrics = self.meter.summarize(
            self.meter.checkpoint_events(checkpoint_again, "s1"), "s1")
        self.assertEqual(metrics["total"]["input"], 3000)
        self.assertEqual(metrics["total"]["output"], 300)

    def test_dual_path_verifier_passes_matching_recompute(self):
        transcript = Path("session.jsonl")
        write_transcript(transcript)

        events = self.meter.parse_transcript(str(transcript), "s1")
        _, checkpoint = self.meter.apply_delta(events, "s1")
        metrics = self.meter.summarize(self.meter.checkpoint_events(checkpoint, "s1"), "s1")
        result = self.meter.verify_cost(metrics, events)

        self.assertTrue(result["verified"])
        self.assertTrue(Path(".raven/.cost-verify.json").exists())

    def test_claude_style_message_usage_shape(self):
        transcript = Path("claude.jsonl")
        write_rows(transcript, [{
            "uuid": "c1",
            "sessionId": "claude-session",
            "type": "assistant",
            "message": {
                "model": "claude-sonnet-4",
                "usage": {
                    "input_tokens": 123,
                    "output_tokens": 45,
                    "cache_read_input_tokens": 10,
                    "cache_creation_input_tokens": 5,
                },
            },
        }])

        events = self.meter.parse_transcript(str(transcript), "fallback")

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].session_id, "claude-session")
        self.assertEqual(events[0].model, "claude-sonnet-4")
        self.assertEqual(events[0].cache_read_tokens, 10)

    def test_openai_codex_top_level_usage_shape(self):
        transcript = Path("codex.jsonl")
        write_rows(transcript, [{
            "id": "o1",
            "session_id": "codex-session",
            "role": "assistant",
            "model": "gpt-4o",
            "usage": {
                "prompt_tokens": 321,
                "completion_tokens": 54,
                "cached_input_tokens": 30,
            },
        }])

        events = self.meter.parse_transcript(str(transcript), "fallback")

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].input_tokens, 321)
        self.assertEqual(events[0].output_tokens, 54)
        self.assertEqual(events[0].cache_read_tokens, 30)

    def test_unknown_grok_style_uses_default_pricing(self):
        transcript = Path("grok.jsonl")
        write_rows(transcript, [{
            "request_id": "grok-1",
            "session_id": "grok-session",
            "response": {
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 50,
                }
            },
            "role": "assistant",
            "model": "grok-unknown",
        }])

        events = self.meter.parse_transcript(str(transcript), "fallback")

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].model, "grok-unknown")
        self.assertEqual(events[0].pricing_source, "default")
        self.assertGreater(events[0].computed_cost_usd, 0)

    def test_alternating_sessions_keep_separate_checkpoints(self):
        a = Path("a.jsonl")
        b = Path("b.jsonl")
        write_rows(a, [{
            "id": "a1",
            "session_id": "session-a",
            "role": "assistant",
            "model": "gpt-4o-mini",
            "usage": {"input_tokens": 100, "output_tokens": 10},
        }])
        write_rows(b, [{
            "id": "b1",
            "session_id": "session-b",
            "role": "assistant",
            "model": "gpt-4o-mini",
            "usage": {"input_tokens": 200, "output_tokens": 20},
        }])

        events_a = self.meter.parse_transcript(str(a), "session-a")
        events_b = self.meter.parse_transcript(str(b), "session-b")
        delta_a, checkpoint = self.meter.apply_delta(events_a, "session-a")
        self.meter.write_json(self.meter.CHECKPOINT_FILE, checkpoint)
        delta_b, checkpoint = self.meter.apply_delta(events_b, "session-b")
        self.meter.write_json(self.meter.CHECKPOINT_FILE, checkpoint)
        delta_a_again, checkpoint = self.meter.apply_delta(events_a, "session-a")

        self.assertEqual(len(delta_a), 1)
        self.assertEqual(len(delta_b), 1)
        self.assertEqual(delta_a_again, [])
        self.assertEqual(len(checkpoint["sessions"]), 2)

    def test_cumulative_cost_uses_checkpoint_not_cost_log_scan(self):
        transcript = Path("session.jsonl")
        write_transcript(transcript)
        events = self.meter.parse_transcript(str(transcript), "s1")
        delta, checkpoint = self.meter.apply_delta(events, "s1")
        session = self.meter.checkpoint_session(checkpoint, "s1")

        self.meter.append_cost_log(delta, session)

        rows = [json.loads(line) for line in Path(".raven/cost-log.jsonl").read_text().splitlines()]
        self.assertEqual(rows[-1]["cumulative_session_cost_usd"], session["cost_totals"]["session_cost_usd"])
        self.assertEqual(
            rows[-1]["cumulative_month_cost_usd"],
            session["cost_totals"]["month_cost_usd"][rows[-1]["turn_timestamp"][:7]],
        )


if __name__ == "__main__":
    unittest.main()
