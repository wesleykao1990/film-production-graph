from __future__ import annotations

import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import prepare_m4  # noqa: E402


class PrepareM4Tests(unittest.TestCase):
    def _arguments(self, *, phase: str = "calibration", mode: str = "dry_run") -> list[str]:
        alias = "story-eval-v1" if mode == "execute_preflight" else "pre-key-model-family"
        provider = (
            "provider-under-test"
            if mode == "execute_preflight"
            else "provider-not-yet-selected"
        )
        model = "model-under-test" if mode == "execute_preflight" else "model-not-yet-selected"
        return [
            "--phase",
            phase,
            "--mode",
            mode,
            "--model-alias",
            alias,
            "--provider",
            provider,
            "--model",
            model,
            "--equal-information-max-calls",
            "1",
            "--equal-information-max-cost-usd",
            "1",
            "--fixed-budget-conventional-max-calls",
            "2",
            "--fixed-budget-conventional-max-cost-usd",
            "1.5",
            "--story-room-max-calls",
            "3",
            "--story-room-max-cost-usd",
            "1",
            "--provenance-destination",
            str(ROOT / "protected-m04a-provenance.json"),
        ]

    def test_calibration_dry_run_compiles_three_requests_without_a_key(self) -> None:
        output = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), redirect_stdout(output):
            result = prepare_m4.main(self._arguments())
        payload = json.loads(output.getvalue())
        self.assertEqual(result, 0)
        self.assertTrue(payload["ready"])
        self.assertEqual(payload["provider_calls_made"], 0)
        self.assertFalse(payload["credential_present"])
        self.assertEqual(len(payload["plan"]["requests"]), 3)

    def test_execute_preflight_fails_closed_without_credential_and_makes_no_call(self) -> None:
        output = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), redirect_stdout(output):
            result = prepare_m4.main(self._arguments(mode="execute_preflight"))
        payload = json.loads(output.getvalue())
        self.assertEqual(result, 2)
        self.assertFalse(payload["ready"])
        self.assertEqual(payload["provider_calls_made"], 0)
        self.assertIn("credential", " ".join(payload["errors"]))

    def test_primary_dry_run_has_all_twenty_seven_declared_requests(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            result = prepare_m4.main(self._arguments(phase="primary"))
        payload = json.loads(output.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(len(payload["plan"]["requests"]), 27)
        self.assertEqual(payload["provider_calls_made"], 0)


if __name__ == "__main__":
    unittest.main()
