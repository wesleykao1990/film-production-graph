import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import StoryRoomPage from "../app/story-room/page";
import {
  FORCED_CHOICES,
  getDecisionInspection,
  getRaterFacingProjection,
  M04A_ADMIN_REVIEW_FIXTURE,
  SCORED_CHOICES,
  serializeRaterFacingProjection,
} from "../src/m04a-review-view-model";

const forbiddenProjectionKeys = new Set([
  "id",
  "projectLabel",
  "briefLabel",
  "candidates",
  "selection",
  "artifacts",
  "taskLabel",
  "assignmentLabel",
  "anchorId",
  "anchor_id",
  "condition",
  "conditionId",
  "mapping",
  "unblinding",
  "correctAnswer",
  "expectedChoice",
]);

const forbiddenProjectionTokens = [
  "candidate-",
  "artifact-",
  "sample-north",
  "sample-south",
  "sample-west",
  "pair-",
  "control-",
  "story_room",
  "equal_information",
  "fixed_budget_conventional",
  "anchor",
];

function collectForbiddenProjectionPaths(
  value: unknown,
  path = "$",
  findings: string[] = [],
): string[] {
  if (Array.isArray(value)) {
    value.forEach((item, index) =>
      collectForbiddenProjectionPaths(item, `${path}[${index}]`, findings),
    );
    return findings;
  }

  if (value !== null && typeof value === "object") {
    Object.entries(value).forEach(([key, item]) => {
      if (forbiddenProjectionKeys.has(key)) {
        findings.push(`${path}.${key}`);
      }
      collectForbiddenProjectionPaths(item, `${path}.${key}`, findings);
    });
    return findings;
  }

  if (typeof value === "string") {
    const normalized = value.toLowerCase();
    for (const token of forbiddenProjectionTokens) {
      if (normalized.includes(token.toLowerCase())) {
        findings.push(`${path} contains ${token}`);
      }
    }
  }
  return findings;
}

describe("M04a offline Story Room review surface", () => {
  it("presents candidate comparison, human rationale, and independent artifact statuses", () => {
    const markup = renderToStaticMarkup(<StoryRoomPage />);

    expect(markup).toContain("Compare premise candidates");
    expect(markup).toContain("Recorded selection rationale");
    expect(markup).toContain("Human-only decision");
    expect(markup).toContain("Validation and approval status");
    expect(markup).toContain("Creative Constitution");
    expect(markup).toContain("Scene Contract");
    expect(markup).toContain("PASS");
    expect(markup).toContain("HUMAN REVIEW");
    expect(markup).toContain("Candidate Cedar");
    expect(markup).toContain("Candidate Marble");
    expect(markup).toContain("Candidate Violet");
    expect(markup).toContain("does not save, approve, or mutate");
  });

  it("keeps the browser-facing projection free of admin and unblinding data", () => {
    const projection = getRaterFacingProjection();
    const findings = collectForbiddenProjectionPaths(projection);

    expect(findings).toEqual([]);
    expect(Object.keys(projection)).toEqual(["assignment", "triplet", "comparisonTask"]);
    expect(projection).not.toHaveProperty("candidates");
    expect(projection).not.toHaveProperty("selection");
    expect(projection).not.toHaveProperty("artifacts");
    expect(projection).not.toHaveProperty("projectLabel");
    expect(projection).not.toHaveProperty("briefLabel");

    const serialized = serializeRaterFacingProjection();
    expect(serialized).toContain("Sample North");
    expect(serialized).toContain("Sample South");
    expect(serialized).toContain("Sample West");
  });

  it("allows ties only for scored pairs and keeps the forced-choice control binary", () => {
    expect(SCORED_CHOICES).toEqual(["left", "tie", "right"]);
    expect(FORCED_CHOICES).toEqual(["left", "right"]);
    expect(
      M04A_ADMIN_REVIEW_FIXTURE.triplet.pairs.every((pair) => pair.choices.includes("tie")),
    ).toBe(true);
    expect(
      M04A_ADMIN_REVIEW_FIXTURE.comparisonTask.dimensions.every(
        (item) => !(item.choices as readonly string[]).includes("tie"),
      ),
    ).toBe(true);
  });

  it("keeps technical problems separate from scored control responses", () => {
    const markup = renderToStaticMarkup(<StoryRoomPage />);
    const controlSection = markup.slice(
      markup.indexOf('aria-labelledby="comparison-title"'),
      markup.indexOf('aria-labelledby="workload-title"'),
    );

    expect(controlSection).toContain("Report technical problem");
    expect(controlSection).toContain("abort and replace");
    expect(controlSection).toContain('type="button"');
    expect(controlSection).not.toContain('value="tie"');
    expect(controlSection).toContain("forced-choice comparison");
    expect(controlSection).not.toContain("anchor");
  });

  it("withholds every preference value after a failed positive control", () => {
    const decision = getDecisionInspection({
      anchorPassed: false,
      preferenceResults: [
        { dimension: "specificity", displayedValue: "91%" },
      ],
    });

    expect(decision).toMatchObject({
      status: "INCONCLUSIVE",
      instrumentStatus: "failed",
      preferenceResultsWithheld: true,
    });
    expect("preferenceResults" in decision).toBe(false);
    expect(JSON.stringify(decision)).not.toContain("91%");

    const markup = renderToStaticMarkup(<StoryRoomPage />);
    expect(markup).toContain("Gate outcome: INCONCLUSIVE");
    expect(markup).toContain("Preference results withheld");
    expect(markup).not.toContain("91%");
  });

  it("exposes workload and timer metadata with keyboard-friendly fieldsets and controls", () => {
    const markup = renderToStaticMarkup(<StoryRoomPage />);

    expect(markup).toContain("Task progress");
    expect(markup).toContain("Task 3 of 5");
    expect(markup).toContain("Elapsed");
    expect(markup).toContain("13:32");
    expect(markup).toContain("≤ 45 minutes");
    expect(markup).toContain("<fieldset");
    expect(markup).toContain('type="radio"');
    expect(markup).toContain('aria-label="Which excerpt is stronger for specificity? response"');
    expect(markup).toContain("Comparison task");
    expect(markup).toContain("forced-choice comparison");
  });

  it("does not put private fixture IDs into rating markup or HTML form names", () => {
    const markup = renderToStaticMarkup(<StoryRoomPage />);
    const privateIds = [
      ...M04A_ADMIN_REVIEW_FIXTURE.candidates.map((candidate) => candidate.id),
      ...M04A_ADMIN_REVIEW_FIXTURE.artifacts.map((artifact) => artifact.id),
      ...M04A_ADMIN_REVIEW_FIXTURE.triplet.samples.map((sample) => sample.id),
      ...M04A_ADMIN_REVIEW_FIXTURE.triplet.pairs.map((pair) => pair.id),
      ...M04A_ADMIN_REVIEW_FIXTURE.comparisonTask.dimensions.map((item) => item.id),
    ];

    for (const privateId of privateIds) {
      expect(markup).not.toContain(privateId);
    }

    const ratingMarkup = markup.slice(
      markup.indexOf('aria-labelledby="triplet-title"'),
      markup.indexOf('aria-labelledby="workload-title"'),
    );
    expect(ratingMarkup).not.toMatch(/(?:id|name)="[^"]*(?:north|south|west|candidate|artifact|pair|control)-/i);
    expect(ratingMarkup).toContain('name="scored-comparison-0"');
    expect(ratingMarkup).toContain('name="forced-comparison-0"');
  });
});
