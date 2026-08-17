# Manual Speaking-Character Feasibility Spike

## Scope

This is a throwaway 5–15 second experiment run in parallel with M04a when the first film requires visible speech. It is not a production adapter and does not need platform code.

## Inputs

- first-film project and target language:
- locked screenplay line and translation/pronunciation notes:
- character/reference image and rights status:
- face angle, movement, shot length, and delivery constraints:
- path tested: canonical audio + lip-sync | native provider dialogue:
- predeclared definition of an acceptable take:

## Run record

- provider/service and resolved model/version:
- date and policy/price snapshot:
- prompt/settings/reference hashes:
- TTS/human/native audio source:
- total attempts submitted:
- technically completed attempts:
- **attempts to first acceptable take:**
- acceptable takes obtained:
- rejected-attempt categories and counts:
  - face/identity drift:
  - mouth-sync or timing failure:
  - wording/pronunciation failure:
  - performance failure:
  - motion/camera artifact:
  - provider/technical failure:
  - other:
- first acceptable output file or asset reference:
- ASR transcript and locked-line diff, when applicable:
- per-attempt and total cost:
- per-attempt and total latency:
- known missing metadata:

## Human verdict

Choose one:

```text
viable
viable_with_constraints
not_viable
not_applicable_no_visible_dialogue
```

Assess:

- word intelligibility;
- timing and mouth alignment;
- recurring voice/character identity;
- face stability and uncanny artifacts;
- target-language pronunciation;
- usable maximum line length and camera constraints;
- whether the result can be repeated rather than obtained as a one-off lucky take.

## Yield and cost implication

Record the observed yield:

```text
acceptable_take_rate = acceptable_takes / technically_completed_attempts
attempts_to_first_acceptable = recorded integer or null if none
```

Use this evidence to update the film Cost Projection. Do not extrapolate from the provider's nominal unit price while assuming one attempt per approved shot.

## Design consequence for M06/M07

Document the production policy this result implies, such as shorter lines, offscreen dialogue, cutaways, human recording, native dialogue preference, canonical TTS plus lip-sync, or no visible speech. State the maximum production assumption that the spike actually supports; do not generalize one successful shot to every face, angle, language, or line length.
