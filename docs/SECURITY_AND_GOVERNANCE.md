# Security and Governance — Final reviewed specification

## 1. Threat model

Primary threats:

- prompt injection in evidence/imported scripts/web content;
- malicious or over-privileged skills;
- cross-project data access;
- approval/lock authority escalation;
- secret exposure;
- provider callback spoofing;
- archive/path attacks in future registry;
- runaway spend;
- rights/consent misuse;
- fabricated provenance;
- release of invalid media.

## 2. Trust classes

### Trusted application policy

Code-reviewed system policy, schemas, agent/tool registry, repository skill instructions, and locked project configuration.

### Untrusted content

Evidence, transcripts, webpages, imported screenplays, model output, provider metadata, comments, and media metadata.

Untrusted content is labeled/delimited and never interpreted as authority. Tool permissions enforce the real boundary.

## 3. Early security gate

M03 must prove untrusted content cannot:

- alter the structured output contract;
- add or invoke undeclared tools;
- approve/lock/release;
- read another project;
- change budgets or provider policy;
- access secrets;
- execute shell/network requests.

This corpus runs on every PR.

## 4. Skill security

Release A accepts only repository-reviewed files. Loader rejects symlinks, path escapes, executable content, oversized resources, invalid schemas, and forbidden permissions. `skills.lock` detects unreviewed changes.

M12 adds upload quarantine and archive-bomb/traversal tests.

## 5. Authority model

Separate capabilities:

```text
read
propose
validate
review
approve
lock
release
administer skills
```

Agents receive only read/propose/validate. Human/policy commands execute approval, lock, and release.

## 6. Secrets and egress

- secrets remain server-side;
- providers use scoped credentials;
- no secrets in prompts/provenance payloads;
- executable capabilities use egress allowlists;
- tests block unexpected external network;
- provider callback signatures and replay protection are verified.

## 7. Spend controls

Budgets apply at project, workflow, step, provider, and user levels. Cost is checked before request and reconciled after response. Exceeding budget requires explicit human override.

## 8. Rights and consent

Voice, likeness, music, reference imagery, stock assets, fonts, SFX, and source evidence require rights records. Provider terms and consent expiry can block use or release.

## 9. Provenance integrity

- content hashes for files and manifests;
- append-only run/cost events;
- manual imports mark unknown data as unknown;
- release sidecar hash matches master;
- optional C2PA signed path is separately tested;
- audit records identify human decisions.

## 10. Hosted-mode controls

M12 adds database RLS, role matrix, tenant-isolation tests, rate limiting, backups/restores, registry quarantine, runtime compatibility, and staging security review.
