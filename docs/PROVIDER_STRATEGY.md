# Model and Media Provider Strategy — Final reviewed specification

## 1. Objective

Keep domain canon provider-neutral and prove a manual production path before automating integrations.

## 2. Provider categories

```text
LLM
image
video
TTS
music
SFX
ASR
lip-sync
cleanup/upscale
storage/import
```

## 3. Model aliases

Release A stores aliases in application config and records the resolved provider/model on every run. Do not deploy a gateway service until centralized routing, budgets, failover, or multiple services justify it.

## 4. Provider policy record

Before use, snapshot:

- commercial-use terms;
- retention/training settings;
- region/data processing constraints;
- voice/likeness restrictions;
- music/film distribution restrictions;
- output ownership/license;
- prohibited uses;
- policy review date/source.

Project policy may block a provider attempt before spend.

## 5. Manual adapter first

M08 flow:

```text
compile bundle
→ export prompt/references/settings/checklist
→ user runs external provider
→ import output
→ enter known metadata
→ unknown remains null/unknown
→ validate media/rights
→ create generation attempt
```

This is a supported adapter, not a temporary hack.

## 6. Core protocols

Automated adapters later implement:

```text
capabilities
compile/validate request
submit
poll or webhook
cancel
normalize result/error
cost record
policy snapshot
```

Provider-specific settings live in compiled request/bundle types.

## 7. Capability matrix

Track:

- image/video duration/resolution/aspect;
- reference character/location support;
- multi-shot support;
- native audio/dialogue;
- language support;
- lip-sync control;
- seed/reproducibility;
- API/webhook availability;
- regional access;
- price snapshot;
- rights/policy status.

The locked Delivery Specification is checked before generation.

## 8. Prompt compilation

Inputs:

```text
locked Shot/Audio/Delivery contracts
approved reference asset hashes
provider capability profile
provider policy
```

Compiler output is immutable and inspectable. It may translate provider syntax but cannot introduce story facts.

A deterministic fact-extraction/diff test compares compiler output against declared entities/actions/state.

## 9. Native dialogue

When supported, native dialogue remains a candidate. The adapter extracts audio, runs ASR, compares text, records speaker/voice diagnostics, and requires human selection. A materially changed line requires screenplay revision.

## 10. Failure/fallback

Normalized errors:

```text
policy_blocked
capability_mismatch
budget_exceeded
rate_limited
timeout
provider_rejected
invalid_output
callback_verification_failed
manual_metadata_incomplete
```

Fallback never silently changes provider, model, price, or rights policy. The new resolved choice is recorded and may require human approval.

## 11. Initial order

1. manual video/image adapter;
2. one real LLM path;
3. one voice/human recording path;
4. ASR when native dialogue is tested;
5. one lip-sync or native-dialogue feasibility adapter;
6. automated video provider only after M08;
7. additional providers based on actual project needs.
