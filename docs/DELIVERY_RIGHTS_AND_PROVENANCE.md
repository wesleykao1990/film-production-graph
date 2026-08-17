# Delivery, Rights, Disclosure, and External Provenance

## 1. Purpose

Prevent the system from discovering release constraints at the final export and expose provenance beyond the internal database.

## 2. Delivery Specification

Lock before final provider generation:

- aspect ratio and dimensions;
- frame rate/time base;
- color and codec expectations;
- audio sample rate/channels/loudness/true peak;
- maximum duration;
- subtitle/caption languages;
- clean/texted master requirements;
- platform/festival file requirements;
- required provenance/disclosure outputs.

Provider capability checks and export validators consume the same artifact.

## 3. Rights gate

Every evidence item and asset has a rights record. Minimum fields:

```text
source and holder
license/permission basis
permitted uses
territory
term/expiry
attribution
commercial/festival/advertising/film permissions
voice/likeness consent
provider terms snapshot
supporting documents
review actor/date
```

Approval requires a populated rights block. Release requires `cleared` for the intended use and territory.

Imported/licensed music is default. Generated music remains disabled until the project explicitly enables it and the provider output license covers the intended distribution.

## 4. Provider policy gate

A provider may be blocked because of training/retention settings, region, commercial-use limits, voice/likeness restrictions, or output terms. Policy snapshots are versioned because terms change.

## 5. Subtitles and captions

Dialogue timing derives subtitle cues. Human review handles reading speed, line breaks, translation, sound descriptions, and speaker attribution.

Required outputs may include:

```text
SRT
WebVTT
burned-in review master
clean master
localized versions
```

## 6. External provenance package

Every release includes:

```text
master file hashes
sidecar provenance JSON
human-readable AI-use disclosure
model/provider/skill summary
rights manifest summary
source manifest hash
subtitle hashes
```

Optional when configured:

- C2PA assertions and signing;
- public verification page;
- timestamp/notary service.

C2PA is one layer, not the only source of truth. Distribution platforms may remove metadata, so the sidecar/public manifest remains available.

## 7. Release blockers

- missing or restricted rights;
- provider policy incompatible with intended use;
- delivery mismatch;
- missing required subtitles;
- final timeline references rejected/unapproved assets;
- provenance manifest hash mismatch;
- material native dialogue difference without screenplay revision;
- expired consent or license.
