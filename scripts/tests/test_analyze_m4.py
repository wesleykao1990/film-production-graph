from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_m4 import AnalysisError, analyze, load_jsonl, load_yaml  # noqa: E402


class AnalyzeM4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        base = ROOT / "examples" / "evals" / "story-room-gate"
        cls.protocol = load_yaml(base / "protocol.yaml")
        cls.manifest = load_yaml(base / "run-manifest.example.yaml")
        cls.ratings = load_jsonl(base / "ratings.example.jsonl")

    def test_executable_example_passes(self) -> None:
        report = analyze(self.protocol, self.manifest, self.ratings)
        self.assertEqual(report["decision"], "PASS")
        self.assertTrue(report["instrument_check"]["valid"])
        self.assertTrue(all(report["primary_requirements"].values()))
        self.assertTrue(report["continuity"]["non_inferior"])
        self.assertFalse(report["preference_results_withheld"])

    def test_failed_anchor_control_is_inconclusive_and_withholds_preferences(self) -> None:
        ratings = copy.deepcopy(self.ratings)
        for record in ratings:
            if record.get("record_type") != "anchor":
                continue
            degraded_choice = (
                "left" if record["anchor_id"] == "ANCHOR-SPECIFICITY-VOICE" else "right"
            )
            for item in record["anchor_ratings"]:
                item["choice"] = degraded_choice
        report = analyze(self.protocol, self.manifest, ratings)
        self.assertEqual(report["decision"], "INCONCLUSIVE")
        self.assertFalse(report["instrument_check"]["valid"])
        self.assertTrue(report["preference_results_withheld"])
        self.assertIsNone(report["preferences"])
        self.assertIsNone(report["primary_requirements"])


    def test_anchor_tie_is_rejected_before_analysis(self) -> None:
        ratings = copy.deepcopy(self.ratings)
        record = next(item for item in ratings if item.get("record_type") == "anchor")
        record["anchor_ratings"][0]["choice"] = "tie"
        with self.assertRaises(AnalysisError):
            analyze(self.protocol, self.manifest, ratings)

    def test_low_scored_item_agreement_is_diagnostic_not_an_inconclusive_gate(self) -> None:
        ratings = copy.deepcopy(self.ratings)
        for record in ratings:
            if record.get("record_type") != "triplet":
                continue
            rater_number = int(record["rater_id"][1:])
            for item in record["primary_ratings"]:
                if rater_number % 3 == 1:
                    item["choice"] = "left"
                elif rater_number % 3 == 2:
                    item["choice"] = "right"
                else:
                    item["choice"] = "tie"
        report = analyze(self.protocol, self.manifest, ratings)
        self.assertNotEqual(report["decision"], "INCONCLUSIVE")
        self.assertTrue(report["instrument_check"]["valid"])
        self.assertTrue(
            all(not value["gating"] for value in report["reliability_diagnostics"].values())
        )

    def test_missing_primary_rating_record_is_rejected(self) -> None:
        ratings = copy.deepcopy(self.ratings)
        index = next(
            index
            for index, record in enumerate(ratings)
            if record.get("record_type") == "triplet"
        )
        del ratings[index]
        with self.assertRaises(AnalysisError):
            analyze(self.protocol, self.manifest, ratings)

    def test_missing_anchor_rating_record_is_rejected(self) -> None:
        ratings = copy.deepcopy(self.ratings)
        index = next(
            index
            for index, record in enumerate(ratings)
            if record.get("record_type") == "anchor"
        )
        del ratings[index]
        with self.assertRaises(AnalysisError):
            analyze(self.protocol, self.manifest, ratings)


if __name__ == "__main__":
    unittest.main()
