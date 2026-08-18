#!/usr/bin/env python3
"""Compile or credential-check an M04a generation plan without calling a provider."""

from __future__ import annotations

import argparse
import json
import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from film_graph.application import (
    CANONICAL_CONDITIONS,
    ExperimentBudget,
    ExperimentFileRef,
    ExperimentModelIdentity,
    ProvenanceDestination,
    preflight_experiment,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = "examples/evals/story-room-gate/protocol.yaml"


def _repository_relative(protocol_path: str, reference: str) -> str:
    candidate = (ROOT / Path(protocol_path).parent / reference).resolve()
    try:
        return candidate.relative_to(ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"protocol reference escapes repository root: {reference}") from exc


def _pin(path: str) -> ExperimentFileRef:
    return ExperimentFileRef.from_file(ROOT, path)


def _optional_pin(path: str) -> ExperimentFileRef | None:
    return _pin(path) if (ROOT / path).is_file() else None


def build_pins(
    protocol: dict[str, Any], protocol_path: str
) -> dict[str, tuple[ExperimentFileRef, ...]]:
    """Discover only protocol-declared and authoritative M04 source files."""

    conditions = protocol.get("conditions")
    if not isinstance(conditions, list):
        raise ValueError("protocol.conditions must be a list")
    prompts = tuple(
        _pin(_repository_relative(protocol_path, str(condition["prompt_path"])))
        for condition in conditions
    )
    brief_paths = [str(protocol["calibration_brief"]), *map(str, protocol["primary_briefs"])]
    briefs = tuple(_pin(_repository_relative(protocol_path, path)) for path in brief_paths)
    pins: dict[str, tuple[ExperimentFileRef, ...]] = {
        "protocol": (_pin(protocol_path),),
        "prompts": prompts,
        "briefs": briefs,
        "rules": (_pin("scripts/m4_rules.py"),),
        "analyzer": (_pin("scripts/analyze_m4.py"),),
    }
    presentation = protocol.get("presentation", {})
    if isinstance(presentation, dict) and presentation.get("assignment_plan"):
        assignment = _optional_pin(
            _repository_relative(protocol_path, str(presentation["assignment_plan"]))
        )
        if assignment:
            pins["assignments"] = (assignment,)
    instrument = protocol.get("instrument_validity", {})
    positive = instrument.get("positive_control", {}) if isinstance(instrument, dict) else {}
    if isinstance(positive, dict) and positive.get("anchor_manifest"):
        anchor = _optional_pin(
            _repository_relative(protocol_path, str(positive["anchor_manifest"]))
        )
        if anchor:
            pins["anchors"] = (anchor,)
    operating = protocol.get("operating_characteristics", {})
    if isinstance(operating, dict):
        if operating.get("script_path"):
            simulator = _optional_pin(
                _repository_relative(protocol_path, str(operating["script_path"]))
            )
            if simulator:
                pins["simulator"] = (simulator,)
        if operating.get("planned_output_path"):
            output = _optional_pin(
                _repository_relative(protocol_path, str(operating["planned_output_path"]))
            )
            if output:
                pins["operating_characteristics"] = (output,)
    return pins


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", default=DEFAULT_PROTOCOL)
    parser.add_argument("--phase", choices=("calibration", "primary"), required=True)
    parser.add_argument(
        "--mode",
        choices=("dry_run", "execute_preflight"),
        default="dry_run",
        help="execute_preflight checks the credential and frozen controls but still makes no call",
    )
    parser.add_argument("--model-alias", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--credential-env", default="M04A_PROVIDER_SECRET")
    for condition in CANONICAL_CONDITIONS:
        option = condition.replace("_", "-")
        parser.add_argument(f"--{option}-max-calls", type=int, required=True)
        parser.add_argument(f"--{option}-max-cost-usd", type=Decimal, required=True)
    parser.add_argument(
        "--provenance-destination",
        default="protected/m04a/provenance.json",
        help="declaration only; this command never creates the destination",
    )
    parser.add_argument("--output", help="optional JSON plan/report output path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    protocol_path = Path(args.protocol).as_posix()
    try:
        raw = yaml.safe_load((ROOT / protocol_path).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("protocol must contain a mapping")
        pins = build_pins(raw, protocol_path)
        budgets = {
            condition: ExperimentBudget(
                max_model_calls=getattr(args, f"{condition}_max_calls"),
                max_cost_usd=getattr(args, f"{condition}_max_cost_usd"),
            )
            for condition in CANONICAL_CONDITIONS
        }
        model = ExperimentModelIdentity(
            alias=args.model_alias,
            provider=args.provider,
            model=args.model,
            credential_env=args.credential_env,
        )
        report = preflight_experiment(
            repository_root=ROOT,
            protocol=raw,
            protocol_path=protocol_path,
            phase=args.phase,
            mode="execute" if args.mode == "execute_preflight" else "dry_run",
            resolved_model=model,
            condition_budgets=budgets,
            pinned_refs=pins,
            environment=os.environ if args.mode == "execute_preflight" else None,
            provenance_destination=ProvenanceDestination(args.provenance_destination),
        )
        payload = {
            "command": "m04a_protected_generation_preflight",
            "provider_calls_made": 0,
            **report.as_dict(),
        }
    except (KeyError, OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        payload = {
            "command": "m04a_protected_generation_preflight",
            "provider_calls_made": 0,
            "ready": False,
            "errors": [f"{type(exc).__name__}: {exc}"],
        }
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8")
    sys.stdout.write(encoded)
    return 0 if payload.get("ready") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
