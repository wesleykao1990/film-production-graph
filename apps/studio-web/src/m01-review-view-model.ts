/**
 * Offline presentation contracts for the M01 review surface.
 *
 * This module deliberately contains no API client and no mutation command. It
 * gives the server-rendered page a stable, typed snapshot to present while the
 * canonical artifact service is integrated in a later slice.
 */

export const M01_MILESTONE = "M01" as const;

export type ArtifactLifecycleStatus =
  | "draft"
  | "validated"
  | "human_review"
  | "approved"
  | "locked"
  | "rejected"
  | "deprecated";

export type ArtifactType =
  | "creative_constitution"
  | "evidence_item"
  | "sequence"
  | "scene_contract";

export type LineageRelation =
  | "DERIVED_FROM"
  | "REQUIRES"
  | "IMPLEMENTS"
  | "USES_ASSET";

export type ImpactClassification =
  | "possibly_stale"
  | "contradicted"
  | "reviewed_valid"
  | "rederive_requested"
  | "resolved";

export type ImpactResolutionStatus =
  | "unresolved"
  | "acknowledged"
  | "revalidate_requested"
  | "rederive_requested"
  | "resolved";

export type RightsStatus =
  | "unverified"
  | "declared"
  | "cleared"
  | "restricted"
  | "expired"
  | "rejected";

export interface ArtifactSummary {
  readonly id: string;
  readonly artifactType: ArtifactType;
  readonly label: string;
  readonly schemaVersion: string;
  readonly revision: number;
  readonly lifecycleStatus: ArtifactLifecycleStatus;
  readonly contentHash: string;
}

export interface LineageEdge {
  readonly sourceArtifactId: string;
  readonly targetArtifactId: string;
  readonly relation: LineageRelation;
}

export interface ImpactReviewItem {
  readonly id: string;
  readonly causeArtifactId: string;
  readonly affectedArtifactId: string;
  readonly classification: ImpactClassification;
  readonly resolutionStatus: ImpactResolutionStatus;
  readonly reason: string;
}

export interface RightsRecordSummary {
  readonly rightsRecordId: string;
  readonly subjectRef: string;
  readonly status: RightsStatus;
  readonly sourceType: string;
  readonly holder: string;
  readonly permittedUses: readonly string[];
  readonly territories: readonly string[];
  readonly reviewedAt: string;
}

export interface AssetRightsSummary {
  readonly id: string;
  readonly label: string;
  readonly intendedUse: string;
  readonly rights: RightsRecordSummary;
}

export interface M01ReviewSnapshot {
  readonly milestone: typeof M01_MILESTONE;
  readonly selectedArtifactId: string;
  readonly artifacts: readonly ArtifactSummary[];
  readonly lineageEdges: readonly LineageEdge[];
  readonly impacts: readonly ImpactReviewItem[];
  readonly assets: readonly AssetRightsSummary[];
}

export interface LineageSummaryEntry {
  readonly artifactId: string;
  readonly label: string;
  readonly artifactType: ArtifactType;
  readonly relation: LineageRelation;
}

export interface LineageSummary {
  readonly upstream: readonly LineageSummaryEntry[];
  readonly downstream: readonly LineageSummaryEntry[];
}

export interface RightsGateState {
  readonly status: RightsStatus;
  readonly complete: boolean;
  readonly approvalEligible: boolean;
  readonly blocked: boolean;
  readonly label: string;
  readonly explanation: string;
}

const lockedHash = (character: string): string => character.repeat(64);

/**
 * A deterministic, illustrative snapshot for the first review surface.
 * It is intentionally labeled as a snapshot in the page; these records are
 * not pretending to be the current database state.
 */
export const M01_REVIEW_SNAPSHOT: M01ReviewSnapshot = {
  milestone: M01_MILESTONE,
  selectedArtifactId: "sequence-blue-pen-v1",
  artifacts: [
    {
      id: "constitution-blue-pen-v1",
      artifactType: "creative_constitution",
      label: "Creative Constitution",
      schemaVersion: "1.0",
      revision: 1,
      lifecycleStatus: "locked",
      contentHash: lockedHash("1"),
    },
    {
      id: "evidence-blue-pen-v1",
      artifactType: "evidence_item",
      label: "Evidence Item",
      schemaVersion: "1.0",
      revision: 1,
      lifecycleStatus: "locked",
      contentHash: lockedHash("2"),
    },
    {
      id: "sequence-blue-pen-v1",
      artifactType: "sequence",
      label: "Sequence",
      schemaVersion: "1.0",
      revision: 1,
      lifecycleStatus: "locked",
      contentHash: lockedHash("3"),
    },
    {
      id: "scene-contract-blue-pen-v1",
      artifactType: "scene_contract",
      label: "Scene Contract",
      schemaVersion: "1.0",
      revision: 1,
      lifecycleStatus: "locked",
      contentHash: lockedHash("4"),
    },
  ],
  lineageEdges: [
    {
      sourceArtifactId: "constitution-blue-pen-v1",
      targetArtifactId: "sequence-blue-pen-v1",
      relation: "REQUIRES",
    },
    {
      sourceArtifactId: "evidence-blue-pen-v1",
      targetArtifactId: "sequence-blue-pen-v1",
      relation: "DERIVED_FROM",
    },
    {
      sourceArtifactId: "sequence-blue-pen-v1",
      targetArtifactId: "scene-contract-blue-pen-v1",
      relation: "IMPLEMENTS",
    },
  ],
  impacts: [
    {
      id: "impact-constitution-to-sequence",
      causeArtifactId: "constitution-blue-pen-v1",
      affectedArtifactId: "sequence-blue-pen-v1",
      classification: "possibly_stale",
      resolutionStatus: "unresolved",
      reason: "The upstream constitution revision may change the sequence constraint set.",
    },
    {
      id: "impact-evidence-to-sequence",
      causeArtifactId: "evidence-blue-pen-v1",
      affectedArtifactId: "sequence-blue-pen-v1",
      classification: "reviewed_valid",
      resolutionStatus: "resolved",
      reason: "Human review confirmed the existing sequence still reflects this evidence snapshot.",
    },
    {
      id: "impact-sequence-to-scene",
      causeArtifactId: "sequence-blue-pen-v1",
      affectedArtifactId: "scene-contract-blue-pen-v1",
      classification: "rederive_requested",
      resolutionStatus: "rederive_requested",
      reason: "A human requested a fresh Scene Contract proposal from the revised sequence.",
    },
  ],
  assets: [
    {
      id: "asset-reference-portrait",
      label: "Reference portrait · S07",
      intendedUse: "internal_development",
      rights: {
        rightsRecordId: "rights-reference-portrait",
        subjectRef: "asset-reference-portrait",
        status: "unverified",
        sourceType: "unknown",
        holder: "Rights holder confirmation pending",
        permittedUses: [],
        territories: [],
        reviewedAt: "2026-08-18T00:00:00Z",
      },
    },
  ],
};

const findArtifact = (
  snapshot: M01ReviewSnapshot,
  artifactId: string,
): ArtifactSummary | undefined =>
  snapshot.artifacts.find((artifact) => artifact.id === artifactId);

/** Return direct incoming and outgoing edges for the selected artifact. */
export function getLineageSummary(
  snapshot: M01ReviewSnapshot,
  selectedArtifactId = snapshot.selectedArtifactId,
): LineageSummary {
  const upstream = snapshot.lineageEdges
    .filter((edge) => edge.targetArtifactId === selectedArtifactId)
    .flatMap((edge) => {
      const artifact = findArtifact(snapshot, edge.sourceArtifactId);
      return artifact
        ? [
            {
              artifactId: artifact.id,
              label: artifact.label,
              artifactType: artifact.artifactType,
              relation: edge.relation,
            },
          ]
        : [];
    });
  const downstream = snapshot.lineageEdges
    .filter((edge) => edge.sourceArtifactId === selectedArtifactId)
    .flatMap((edge) => {
      const artifact = findArtifact(snapshot, edge.targetArtifactId);
      return artifact
        ? [
            {
              artifactId: artifact.id,
              label: artifact.label,
              artifactType: artifact.artifactType,
              relation: edge.relation,
            },
          ]
        : [];
    });

  return { upstream, downstream };
}

export function getArtifactById(
  snapshot: M01ReviewSnapshot,
  artifactId: string,
): ArtifactSummary | undefined {
  return findArtifact(snapshot, artifactId);
}

/**
 * Approval review needs a populated rights record. A complete `declared` or
 * `cleared` record is sufficient for that review gate; release clearance is a
 * later check against intended use and territory.
 */
export function isCompleteRightsRecord(
  rights: RightsRecordSummary,
): boolean {
  return Boolean(
    rights.rightsRecordId.trim() &&
      rights.subjectRef.trim() &&
      rights.sourceType.trim() &&
      rights.holder.trim() &&
      rights.permittedUses.length > 0 &&
      rights.territories.length > 0 &&
      rights.reviewedAt.trim(),
  );
}

export function getRightsGateState(asset: AssetRightsSummary): RightsGateState {
  const complete = isCompleteRightsRecord(asset.rights);
  const approvalEligible =
    complete &&
    (asset.rights.status === "declared" || asset.rights.status === "cleared");
  const blocked = !approvalEligible;

  return {
    status: asset.rights.status,
    complete,
    approvalEligible,
    blocked,
    label: blocked ? "Approval blocked" : "Ready for approval review",
    explanation: blocked
      ? "Approval review requires a complete declared or cleared rights record; this snapshot is unverified or incomplete. Release readiness is a separate check and is not claimed here."
      : "This rights record is complete for approval review. Release readiness is a separate check requiring cleared rights for the intended use and territory.",
  };
}
