# Provider Adapter Checklist — Final reviewed specification

## Identity and policy

- provider/model/version:
- capability profile verified at:
- provider policy snapshot:
- commercial-use/film distribution status:
- retention/training status:
- voice/likeness restrictions:
- allowed for this project:

## Protocol support

- [ ] capabilities
- [ ] delivery preflight
- [ ] estimate
- [ ] submit
- [ ] poll/webhook
- [ ] cancel
- [ ] normalize result/error
- [ ] idempotency
- [ ] usage/cost ledger
- [ ] policy snapshot

## Capability mapping

- modalities/references:
- duration/resolution/aspect/FPS:
- multi-shot:
- native audio/dialogue:
- language:
- seed/reproducibility:
- API/webhook:
- regional/rate/concurrency constraints:

## Canon and audio protection

- [ ] provider fields remain adapter-scoped
- [ ] compiler inputs are locked/snapshotted
- [ ] fact-preservation validator
- [ ] Delivery Specification checked before spend
- [ ] shot dialogue source honored
- [ ] native dialogue ASR compared with locked text
- [ ] material text difference requires screenplay revision
- [ ] native components promoted separately
- [ ] fallback is explicit and recorded

## Security and rights

- [ ] server credentials only
- [ ] callback verification/replay protection
- [ ] constrained media download and probe
- [ ] log/secret redaction
- [ ] rights record and provider policy gate
- [ ] egress policy

## Contract tests

- [ ] success
- [ ] policy blocked
- [ ] delivery/capability mismatch
- [ ] rate/transient/permanent failure
- [ ] timeout/cancellation
- [ ] malformed/duplicate callback
- [ ] spend limit
- [ ] unknown manual metadata

## Manual fallback

Describe export/import procedure and which metadata may remain unknown.
