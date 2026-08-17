# Final Validation Report — v3.0.0

## Scope

This report covers the curated final handoff, the unchanged reviewed M04 v2.4 decision tooling, the installable repository skill/workflow examples, and the new runnable reference prototype.

## Commands executed

```bash
PYTHONDONTWRITEBYTECODE=1 python scripts/validate_package.py
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s scripts/tests -v

cd prototype
PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 python -m app.cli smoke
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
curl http://127.0.0.1:8765/api/health
curl http://127.0.0.1:8765/
```

After checksum generation:

```bash
PYTHONDONTWRITEBYTECODE=1 python scripts/validate_package.py --verify-checksums
unzip -t AI_Film_Production_Graph_Final_Package_v3.0.0.zip
```

## Results

| Check | Result |
|---|---:|
| JSON/YAML parse | 96 files, 0 errors |
| Draft 2020-12 schemas | 30 valid |
| Mapped schema instances and response-contract probes | 67 pass |
| Root and example whole-directory skill locks | Pass |
| M04 assignment modes | 9 pass |
| M04 executable analysis fixture | Reproduced exactly |
| M04 operating-characteristics hashes/requirements | Pass |
| M04 analyzer/rule/simulator unit tests | 19/19 pass |
| Prototype tests | 8/8 pass |
| Prototype smoke | 1 project, 10 artifacts, 1 skill, 2 workflows |
| Prototype HTTP health and static UI | Pass |
| Local Markdown links | 18 checked, 0 broken |
| Python compilation | Pass |
| Source checksums | Verified after freeze |
| ZIP integrity | Verified after packaging |

## Prototype behaviors verified

- locked artifact payloads remain unchanged when a new version is created;
- a revision creates graph-reachability impact records for downstream artifacts;
- approval and locking are distinct human actions;
- repository-skill digests change when only a reference file changes;
- the deterministic agent creates a typed `screenplay_patch` in `proposed` status;
- the declarative workflow pauses at `human_approval`;
- untrusted screenplay text cannot grant the agent approval authority;
- resetting restores the deterministic Blue Pen fixture;
- no live model or media-provider call occurs.

## Important interpretation

The prototype is a behavioral reference, not the production system. Its passing tests do not satisfy M00 or any later milestone. The production build must still implement the reviewed Next.js/FastAPI/Supabase architecture and prove each milestone exit gate.

The checked-in M04 outputs are mechanical fixtures. A real M04a experiment remains unfrozen until calibration material, a two-rater pilot, pilot-informed operating characteristics, frozen anchors/assignments, and named human review are completed.
