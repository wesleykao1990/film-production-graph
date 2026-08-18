/**
 * Offline, rater-safe presentation contracts for the M04a Story Room gate.
 *
 * The experiment's confidential mapping is intentionally not represented by
 * these types.  The page receives only opaque display labels and the
 * pre-declared measurement rules.  There is no API client, persistence
 * command, or unblinding helper in this module.
 */

export const M04A_MILESTONE = "M04a" as const;

export type CandidateReviewStatus =
  | "validated"
  | "human_review"
  | "selected"
  | "not_selected";

export type ValidationStatus = "passed" | "needs_review";

export type ApprovalStatus =
  | "approved"
  | "human_review"
  | "pending"
  | "rejected";

export type RatingDimension =
  | "specificity"
  | "character_voice"
  | "causal_progression";

export type ScoredChoice = "left" | "right" | "tie";
export type ForcedChoice = Exclude<ScoredChoice, "tie">;

export const PRIMARY_DIMENSIONS: readonly RatingDimension[] = [
  "specificity",
  "character_voice",
  "causal_progression",
];

export const SCORED_CHOICES: readonly ScoredChoice[] = [
  "left",
  "tie",
  "right",
];

export const FORCED_CHOICES: readonly ForcedChoice[] = ["left", "right"];

export interface CandidateCard {
  readonly id: string;
  readonly label: string;
  readonly logline: string;
  readonly strengths: readonly string[];
  readonly openQuestion: string;
  readonly reviewStatus: CandidateReviewStatus;
}

export interface HumanSelectionRecord {
  readonly selectedCandidateId: string;
  readonly rationale: string;
  readonly recordedBy: "human";
  readonly recordedAt: string;
  readonly presentationNote: string;
}

export interface ArtifactReviewStatus {
  readonly id: string;
  readonly label: string;
  readonly versionLabel: string;
  readonly validation: ValidationStatus;
  readonly approval: ApprovalStatus;
  readonly detail: string;
}

/** Internal/admin-only sample record. Never pass this shape to the rater. */
interface AdminSample {
  readonly id: string;
  readonly displayLabel: string;
  readonly excerpt: string;
}

/** Internal/admin-only pair record. The id is deliberately stripped below. */
interface AdminScoredPairTask {
  readonly id: string;
  readonly dimension: RatingDimension;
  readonly prompt: string;
  readonly leftSample: AdminSample;
  readonly rightSample: AdminSample;
  readonly choices: readonly ScoredChoice[];
}

interface AdminTripletTask {
  readonly taskLabel: string;
  readonly samples: readonly AdminSample[];
  readonly pairs: readonly AdminScoredPairTask[];
  readonly instructions: string;
}

interface AdminComparisonTask {
  readonly taskLabel: string;
  readonly dimensions: readonly {
    readonly id: string;
    readonly dimension: RatingDimension;
    readonly prompt: string;
    readonly leftSample: AdminSample;
    readonly rightSample: AdminSample;
    readonly choices: readonly ForcedChoice[];
  }[];
  readonly instructions: string;
  readonly technicalProblemAction: string;
}

/** The only sample fields that cross into a rater-facing browser surface. */
export interface RaterSample {
  readonly displayLabel: string;
  readonly excerpt: string;
}

export interface RaterScoredPairTask {
  readonly dimension: RatingDimension;
  readonly prompt: string;
  readonly leftSample: RaterSample;
  readonly rightSample: RaterSample;
  readonly choices: readonly ScoredChoice[];
}

export interface RaterTripletTask {
  readonly instructions: string;
  readonly samples: readonly RaterSample[];
  readonly pairs: readonly RaterScoredPairTask[];
}

export interface RaterComparisonTask {
  readonly dimensions: readonly {
    readonly dimension: RatingDimension;
    readonly prompt: string;
    readonly leftSample: RaterSample;
    readonly rightSample: RaterSample;
    readonly choices: readonly ForcedChoice[];
  }[];
  readonly instructions: string;
  readonly technicalProblemAction: string;
}

export interface AssignmentWorkload {
  readonly assignmentLabel: string;
  readonly taskPosition: string;
  readonly completedTaskCount: number;
  readonly totalTaskCount: number;
  readonly scoredJudgmentsPerTriplet: number;
  readonly elapsedSeconds: number;
  readonly elapsedLabel: string;
  readonly targetMinutes: number;
}

/** Assignment metadata safe to show while a rater completes a task. */
export interface RaterWorkload {
  readonly taskPosition: string;
  readonly completedTaskCount: number;
  readonly totalTaskCount: number;
  readonly scoredJudgmentsPerTriplet: number;
  readonly elapsedSeconds: number;
  readonly elapsedLabel: string;
  readonly targetMinutes: number;
}

export interface InstrumentStatus {
  readonly label: string;
  readonly status: "failed" | "ready";
  readonly summary: string;
}

export type DecisionInspection =
  | {
      readonly status: "PASS" | "MIXED" | "FAIL";
      readonly label: string;
      readonly instrumentStatus: "ready";
      readonly summary: string;
      readonly preferenceResults: readonly {
        readonly dimension: RatingDimension;
        readonly displayedValue: string;
      }[];
    }
  | {
      readonly status: "INCONCLUSIVE";
      readonly label: string;
      readonly instrumentStatus: "failed";
      readonly summary: string;
      readonly preferenceResultsWithheld: true;
    };

/** Admin review data used by the offline studio sections. */
export interface M04AAdminReviewFixture {
  readonly milestone: typeof M04A_MILESTONE;
  readonly mode: "offline_fixture";
  readonly projectLabel: string;
  readonly briefLabel: string;
  readonly candidates: readonly CandidateCard[];
  readonly selection: HumanSelectionRecord;
  readonly artifacts: readonly ArtifactReviewStatus[];
  readonly assignment: AssignmentWorkload;
  readonly triplet: AdminTripletTask;
  readonly comparisonTask: AdminComparisonTask;
  readonly instrument: InstrumentStatus;
  readonly decision: DecisionInspection;
}

/** Strict browser-facing projection: only rating material and workload remain. */
export interface RaterFacingProjection {
  readonly assignment: RaterWorkload;
  readonly triplet: RaterTripletTask;
  readonly comparisonTask: RaterComparisonTask;
}

/**
 * The exact input accepted by the pure decision helper is deliberately small.
 * A caller can provide a boolean from a future analyzer without exposing its
 * confidential details to this view model.
 */
export interface DecisionInput {
  readonly anchorPassed?: boolean;
  readonly instrumentPassed?: boolean;
  readonly statusWhenValid?: "PASS" | "MIXED" | "FAIL";
  readonly preferenceResults?: readonly {
    readonly dimension: RatingDimension;
    readonly displayedValue: string;
  }[];
}

/**
 * Apply the instrument gate before preference values can be inspected.
 * An instrument failure returns a different union branch with no preference
 * result field at all, making accidental display of scored values impossible.
 */
export function getDecisionInspection(input: DecisionInput): DecisionInspection {
  const instrumentPassed = input.anchorPassed ?? input.instrumentPassed ?? false;

  if (!instrumentPassed) {
    return {
      status: "INCONCLUSIVE",
      label: "INCONCLUSIVE",
      instrumentStatus: "failed",
      summary:
        "The measurement instrument did not pass its pre-declared check. Preference results are withheld until measurement is repaired under a new protocol.",
      preferenceResultsWithheld: true,
    };
  }

  const status = input.statusWhenValid ?? "PASS";
  return {
    status,
    label: status,
    instrumentStatus: "ready",
    summary: "The instrument passed; preference results may be inspected by the authorized analysis path.",
    preferenceResults: input.preferenceResults ?? [],
  };
}

/** Short alias for callers that prefer a verb describing the pure operation. */
export const inspectDecision = getDecisionInspection;

const sample = (
  id: string,
  displayLabel: string,
  excerpt: string,
): AdminSample => ({ id, displayLabel, excerpt });

const sampleNorth = sample(
  "sample-north",
  "Sample North",
  "The key stays in the envelope. Mara folds the receipt twice, then asks who taught the clerk to count backward.",
);
const sampleSouth = sample(
  "sample-south",
  "Sample South",
  "Mara enters the office and notices the envelope. She asks for the key, and the clerk says it is not there.",
);
const sampleWest = sample(
  "sample-west",
  "Sample West",
  "The receipt is warm from the printer. Mara hides it in her sleeve while the clerk reaches for the door latch.",
);

const scoredPair = (
  id: string,
  dimension: RatingDimension,
  leftSample: AdminSample,
  rightSample: AdminSample,
): AdminScoredPairTask => ({
  id,
  dimension,
  prompt: `Which excerpt is stronger for ${dimension.replaceAll("_", " ")}?`,
  leftSample,
  rightSample,
  choices: SCORED_CHOICES,
});

/**
 * A deterministic, intentionally small fixture.  Candidate and rating labels
 * are opaque presentation labels; no condition, mapping, expected response,
 * or control identity is present.
 */
export const M04A_ADMIN_REVIEW_FIXTURE: M04AAdminReviewFixture = {
  milestone: M04A_MILESTONE,
  mode: "offline_fixture",
  projectLabel: "Blue Pen / Story Room",
  briefLabel: "Brief 04 · The missing receipt",
  candidates: [
    {
      id: "candidate-cedar",
      label: "Candidate Cedar",
      logline:
        "A records clerk risks a trusted friendship to prove that a missing receipt was counted on purpose.",
      strengths: ["Specific object pressure", "A visible choice with a cost"],
      openQuestion: "Can the final turn remain legible without explaining the ledger?",
      reviewStatus: "selected",
    },
    {
      id: "candidate-marble",
      label: "Candidate Marble",
      logline:
        "A late-night handoff forces two colleagues to decide whether accuracy matters more than loyalty.",
      strengths: ["Immediate relationship pressure", "Contained location"],
      openQuestion: "The objective may need a more singular physical detail.",
      reviewStatus: "not_selected",
    },
    {
      id: "candidate-violet",
      label: "Candidate Violet",
      logline:
        "A pattern-minded clerk follows a small accounting error into a confrontation with her former mentor.",
      strengths: ["Distinctive professional behavior", "Strong character history"],
      openQuestion: "The causal turn needs a sharper irreversible consequence.",
      reviewStatus: "not_selected",
    },
  ],
  selection: {
    selectedCandidateId: "candidate-cedar",
    rationale:
      "Candidate Cedar makes the causal test concrete: the receipt is both a specific object and the pressure point in Mara's relationship choice.",
    recordedBy: "human",
    recordedAt: "2026-08-18 09:40 UTC",
    presentationNote:
      "Shown as a recorded human decision for review. This offline surface does not save, approve, or mutate a project.",
  },
  artifacts: [
    {
      id: "artifact-constitution",
      label: "Creative Constitution",
      versionLabel: "v1 · locked snapshot",
      validation: "passed",
      approval: "approved",
      detail: "Evidence and authorial constraints are present.",
    },
    {
      id: "artifact-evidence",
      label: "Evidence Bank",
      versionLabel: "v1 · locked snapshot",
      validation: "passed",
      approval: "approved",
      detail: "Source notes carry provenance and rights references.",
    },
    {
      id: "artifact-premise",
      label: "Premise Candidate Set",
      versionLabel: "v1 · comparison snapshot",
      validation: "passed",
      approval: "human_review",
      detail: "Independent branches remain visible after selection.",
    },
    {
      id: "artifact-scene-contract",
      label: "Scene Contract",
      versionLabel: "v1 · review snapshot",
      validation: "passed",
      approval: "pending",
      detail: "Objective, opposition, turn, and state delta are ready for review.",
    },
  ],
  assignment: {
    assignmentLabel: "Assignment 04",
    taskPosition: "Task 3 of 5",
    completedTaskCount: 2,
    totalTaskCount: 5,
    scoredJudgmentsPerTriplet: 3,
    elapsedSeconds: 812,
    elapsedLabel: "13:32",
    targetMinutes: 45,
  },
  triplet: {
    taskLabel: "Matched triplet · Task 3",
    instructions:
      "Read the same middle-scene excerpt in each opaque sample. For every question, choose the left sample, right sample, or tie. Use the text only; do not infer authorship or process.",
    samples: [sampleNorth, sampleSouth, sampleWest],
    pairs: [
      scoredPair("pair-specificity-one", "specificity", sampleNorth, sampleSouth),
      scoredPair("pair-specificity-two", "specificity", sampleWest, sampleNorth),
      scoredPair("pair-voice-one", "character_voice", sampleNorth, sampleWest),
      scoredPair("pair-voice-two", "character_voice", sampleSouth, sampleNorth),
      scoredPair("pair-causality-one", "causal_progression", sampleWest, sampleSouth),
      scoredPair("pair-causality-two", "causal_progression", sampleNorth, sampleWest),
    ],
  },
  comparisonTask: {
    taskLabel: "Comparison task",
    instructions:
      "Choose the stronger of the two samples for the named dimension. This is a forced-choice comparison. If either excerpt is missing, unreadable, or technically defective, report the problem instead of guessing.",
    dimensions: [
      {
        id: "control-specificity",
        dimension: "specificity",
        prompt: "Which sample is stronger for specificity?",
        leftSample: sampleSouth,
        rightSample: sampleNorth,
        choices: FORCED_CHOICES,
      },
      {
        id: "control-causality",
        dimension: "causal_progression",
        prompt: "Which sample is stronger for causal progression?",
        leftSample: sampleWest,
        rightSample: sampleSouth,
        choices: FORCED_CHOICES,
      },
    ],
    technicalProblemAction:
      "Report technical problem — abort and replace this task before the dataset is frozen",
  },
  instrument: {
    label: "Measurement instrument",
    status: "failed",
    summary:
      "One deterministic offline failure fixture is shown so the withheld-results branch can be inspected.",
  },
  decision: getDecisionInspection({ anchorPassed: false }),
};

/** Backwards-friendly admin names for callers that use snapshot terminology. */
export const M04A_REVIEW_FIXTURE = M04A_ADMIN_REVIEW_FIXTURE;
export const M04A_REVIEW_SNAPSHOT = M04A_ADMIN_REVIEW_FIXTURE;

/**
 * Return only data suitable for a browser-facing rater.  The explicit copy is
 * useful when a future adapter receives a larger private record: it makes the
 * boundary auditable and prevents accidental spreading of private fields.
 */
export function getRaterFacingProjection(
  fixture: M04AAdminReviewFixture = M04A_ADMIN_REVIEW_FIXTURE,
): RaterFacingProjection {
  const projectSample = (item: AdminSample): RaterSample => ({
    displayLabel: item.displayLabel,
    excerpt: item.excerpt,
  });

  return {
    assignment: {
      taskPosition: fixture.assignment.taskPosition,
      completedTaskCount: fixture.assignment.completedTaskCount,
      totalTaskCount: fixture.assignment.totalTaskCount,
      scoredJudgmentsPerTriplet: fixture.assignment.scoredJudgmentsPerTriplet,
      elapsedSeconds: fixture.assignment.elapsedSeconds,
      elapsedLabel: fixture.assignment.elapsedLabel,
      targetMinutes: fixture.assignment.targetMinutes,
    },
    triplet: {
      instructions: fixture.triplet.instructions,
      samples: fixture.triplet.samples.map(projectSample),
      pairs: fixture.triplet.pairs.map((pair) => ({
        dimension: pair.dimension,
        prompt: pair.prompt,
        leftSample: projectSample(pair.leftSample),
        rightSample: projectSample(pair.rightSample),
        choices: [...pair.choices],
      })),
    },
    comparisonTask: {
      instructions: fixture.comparisonTask.instructions,
      dimensions: fixture.comparisonTask.dimensions.map((item) => ({
        dimension: item.dimension,
        prompt: item.prompt,
        leftSample: projectSample(item.leftSample),
        rightSample: projectSample(item.rightSample),
        choices: [...item.choices],
      })),
      technicalProblemAction: fixture.comparisonTask.technicalProblemAction,
    },
  };
}

/** Stable serialized form for boundary tests and future transport adapters. */
export function serializeRaterFacingProjection(
  fixture: M04AAdminReviewFixture = M04A_ADMIN_REVIEW_FIXTURE,
): string {
  return JSON.stringify(getRaterFacingProjection(fixture));
}

export function formatElapsedTime(totalSeconds: number): string {
  const safeSeconds = Math.max(0, Math.floor(totalSeconds));
  const minutes = Math.floor(safeSeconds / 60);
  const seconds = safeSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}
