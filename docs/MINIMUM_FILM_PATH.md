# Minimum Path to One Finished Film

## 1. Goal

Produce a watchable 60–180 second film with honest lineage without waiting for the full platform.

## 2. Required subset

```text
M00 Foundation Lite
M01 Artifacts/lineage/rights/impact
M02 Repository skills
M03 Agent runtime/security
M04a minimum Story Room gate
M04b conditional Story Room completion
M06-lite Audio/Delivery/Subtitles
M07 Storyboard/Animatic/productionized dialogue path
M08 Manual provider export/import and release
```

M05 durable workflows may be skipped for a one-off private film if run state is simple and manually recoverable. M09 automated providers, M10 full Studio, and M12 hosted registry are not required.

## 3. Operational flow

1. Lock the Creative Constitution, Evidence Bank, Delivery Specification, and Budget Plan.
2. Complete M04a and record PASS; then complete M04b.
3. Lock premise, characters, relationships, beats, sequence, scenes, and screenplay.
4. Select dialogue mode per shot.
5. Approve Voice Profiles, dialogue assets, music cue, ambience, and SFX.
6. Produce storyboard and audio animatic.
7. Before M06, use the manual M04a spike result—including attempts to first acceptable take—to choose the dialogue policy and seed the cost projection; in M07, reproduce that path through the application boundary.
8. Export provider bundles manually.
9. Import outputs and enter known metadata; leave unavailable fields unknown.
10. Select takes and assemble in FFmpeg or the target NLE.
11. Generate and review subtitles.
12. Validate duration, frame rate, dimensions, loudness, true peak, language tracks, and required masters.
13. Validate rights.
14. Export master, clean master if needed, subtitle files, human AI-use disclosure, and provenance sidecar.

## 4. Minimum UI

A full graph canvas is unnecessary. The minimum UI needs:

- artifact form/editor;
- version history and diff;
- approval/rejection;
- premise/sample comparison;
- blind-rating screen;
- prompt-bundle export;
- manual output import;
- release checklist.

CLI/admin scripts may cover non-creative operations.

## 5. Minimum provider support

- one direct LLM integration or manual model runner;
- fake TTS for CI plus one real TTS/human recording path;
- one manual image/video provider path;
- one ASR path when native dialogue is used;
- one lip-sync/native-dialogue feasibility path when visible speech is required;
- FFmpeg/ffprobe;
- optional target NLE.

## 6. Stopping point

After a successful M08 export, decide whether repeated use justifies automated provider adapters and the full Studio. Do not assume that one film requires a SaaS platform.
