# Audio Continuity Specification — Final reviewed specification

## 1. Objective

Treat voice, dialogue performance, music, ambience, Foley, and SFX as persistent timeline assets rather than incidental audio generated independently with each shot.

## 2. Audio graph

```text
Character → Voice Profile → Voice Performance → Dialogue Asset
Sequence/Scene → Music Cue → Stems
Location State → Ambience Profile → Ambience Asset
Prop/Action → Foley or SFX Cue → Asset
All approved assets → Audio Timeline → Release mix
```

## 3. Dialogue source policy

Every Shot Contract declares one:

```text
canonical_tts
human_recording
native_provider_dialogue
no_on_camera_dialogue
```

### Canonical TTS

Locked line → persistent Voice Profile → performance settings → WAV → picture → lip-sync if visible.

### Human recording

Locked line → performer/consent/rights → recorded takes → human select → picture/lip-sync as needed.

### Native provider dialogue

Locked line → provider audiovisual generation → ASR transcript → text diff → voice/performance review → explicit promotion.

If the spoken words materially differ, either reject the take or approve a screenplay revision first. Audio cannot silently rewrite canon.

## 4. Voice identity and performance

Voice Profile owns stable identity:

```text
timbre/register/accent
baseline cadence and speech fingerprint
reference/consent/rights
pronunciation dictionary
provider strategy
```

Voice Performance owns line-specific behavior:

```text
emotion/intensity
pace/pauses/emphasis
volume/breath/effort
context such as whispering or running
```

Changing performance does not create a new identity unless human review says it does.

## 5. Music

Music attaches to a `sequence`, `scene`, or timeline range—not a shot.

The Music Bible contains:

- dramatic principle;
- palette;
- forbidden defaults;
- harmonic/rhythmic language;
- motifs and transformations;
- cue plan;
- stems;
- rights source.

Default v1 policy:

```text
imported_or_licensed_music = enabled
generated_music = disabled
```

Generated music requires explicit project enablement, provider policy review, and rights clearance for the intended film use.

## 6. Ambience and acoustics

A Location State has an acoustic profile and continuous ambience bed across cuts. Perspective/reverb may change per shot while the underlying environment remains coherent.

Validators detect unintended gaps, abrupt profile changes, and inconsistent recurring sounds.

## 7. Foley and SFX

Cues are time-anchored and identify source entity, action, material, perspective, story function, and preferred asset. Provider-native Foley/SFX may be extracted and promoted separately from native dialogue/music.

## 8. Native component policy

```yaml
native_audio:
  dialogue: discard | candidate | preferred
  foley: discard | candidate | preferred
  sfx: discard | candidate | preferred
  ambience: discard | candidate | preferred
  music: discard
```

A component can be selected without promoting the entire native mix.

## 9. Speaking-character feasibility in two stages

### M04a manual learning spike

When the actual first film requires visible speech, run a throwaway 5–15 second experiment before designing the productionized audio path. It needs no platform code. Record target language, locked line, reference/rights, provider/model/settings, every attempt, rejection reason, attempts to first acceptable take, output, ASR diff where applicable, cost/latency, and one verdict: viable, viable with constraints, not viable, or not applicable.

The result may change the production policy toward shorter lines, cutaways, offscreen speech, human recording, native dialogue, or canonical TTS plus lip-sync. This is exactly why it occurs before M06.

### M07 productionized proof

M07 repeats the selected path through the real application/provider boundary with complete provenance, validation, and reproducibility. The storyboard animatic can pass without visible dialogue; the production path cannot claim it is supported until this repeat succeeds.

## 10. Subtitle derivation

Canonical dialogue plus timeline timing produces a versioned Subtitle Track. Human review handles line breaks, reading speed, speaker ambiguity, translation, and non-speech captions. Export SRT/VTT and optional burn-in.

## 11. Internal audio timeline

The application timeline represents dialogue alternatives, stems, ambience, cues, gains/fades, and selected assets. It can project editorial timing to OTIO while retaining richer audio state internally.

## 12. Hard validators

- approved dialogue references approved Voice Profile/recording rights;
- native transcript matches locked text within configured tolerance;
- material mismatch has approved screenplay revision;
- cue target sequence/scene exists;
- no ambience gaps unless intentional;
- no audio asset without rights block;
- generated music feature flag and rights satisfied;
- output meets sample rate/channel/loudness/true-peak delivery targets;
- picture replacement does not change approved audio references.

## 13. Human diagnostics

- recurring speaker sounds like the same person;
- performances remain expressive rather than normalized;
- music has motif/palette continuity;
- soundtrack supports dramatic state rather than narrating emotion generically;
- ambience masks independent picture generation seams;
- native and canonical paths are compared per shot rather than by ideology.
