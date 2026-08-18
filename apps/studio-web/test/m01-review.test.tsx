import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import HomePage from "../app/page";
import {
  getLineageSummary,
  getRightsGateState,
  M01_REVIEW_SNAPSHOT,
  type AssetRightsSummary,
} from "../src/m01-review-view-model";

const completeRightsAsset = (
  status: "declared" | "cleared",
): AssetRightsSummary => ({
  id: `asset-${status}`,
  label: `Complete ${status} asset`,
  intendedUse: "internal_development",
  rights: {
    rightsRecordId: `rights-${status}`,
    subjectRef: `asset-${status}`,
    status,
    sourceType: "licensed",
    holder: "Production Studio",
    permittedUses: ["internal_development"],
    territories: ["Worldwide"],
    reviewedAt: "2026-08-18T00:00:00Z",
  },
});

describe("M01 review studio presentation", () => {
  it("renders the four locked canon artifacts and retains human-only authority", () => {
    const markup = renderToStaticMarkup(<HomePage />);

    expect(markup).toContain("M01 canon overview");
    for (const label of [
      "Creative Constitution",
      "Evidence Item",
      "Sequence",
      "Scene Contract",
    ]) {
      expect(markup).toContain(label);
    }
    expect(markup).toContain("locked · immutable");
    expect(markup).toContain("Approval and lock transitions are");
    expect(markup).toContain("human-only");
    expect(markup).toContain("grants no agent approval authority");
  });

  it("shows bidirectional lineage and keeps impact resolution separate", () => {
    const markup = renderToStaticMarkup(<HomePage />);
    const lineage = getLineageSummary(M01_REVIEW_SNAPSHOT);

    expect(lineage.upstream.map((entry) => entry.label)).toEqual([
      "Creative Constitution",
      "Evidence Item",
    ]);
    expect(lineage.downstream.map((entry) => entry.label)).toEqual([
      "Scene Contract",
    ]);
    expect(markup).toContain("Bidirectional lineage");
    expect(markup).toContain("Incoming / upstream");
    expect(markup).toContain("Outgoing / downstream");
    expect(markup).toContain("possibly_stale");
    expect(markup).toContain("unresolved");
    expect(markup).toContain("reviewed_valid");
    expect(markup).toContain("rederive_requested");
    expect(markup).toContain("Impact records describe possible upstream consequences");
    expect(markup).toContain("separate from artifact lifecycle");
  });

  it("blocks asset approval when the rights record is unverified or incomplete", () => {
    const markup = renderToStaticMarkup(<HomePage />);
    const asset = M01_REVIEW_SNAPSHOT.assets[0];

    expect(asset).toBeDefined();
    expect(getRightsGateState(asset).blocked).toBe(true);
    expect(markup).toContain("Asset rights gate");
    expect(markup).toContain("Rights-blocked state");
    expect(markup).toContain("Approval blocked");
    expect(markup).toContain("unverified · unverified / incomplete");
    expect(markup).toContain("requires a complete declared or cleared rights record");
  });

  it("allows complete declared and cleared records into approval review only", () => {
    const declared = completeRightsAsset("declared");
    const cleared = completeRightsAsset("cleared");
    const incompleteDeclared: AssetRightsSummary = {
      ...declared,
      id: "asset-incomplete-declared",
      rights: {
        ...declared.rights,
        holder: "",
        permittedUses: [],
      },
    };
    const unverified = M01_REVIEW_SNAPSHOT.assets[0];

    expect(getRightsGateState(declared)).toMatchObject({
      complete: true,
      approvalEligible: true,
      blocked: false,
    });
    expect(getRightsGateState(cleared)).toMatchObject({
      complete: true,
      approvalEligible: true,
      blocked: false,
    });
    expect(getRightsGateState(cleared).explanation).toContain(
      "Release readiness is a separate check",
    );
    expect(getRightsGateState(incompleteDeclared)).toMatchObject({
      complete: false,
      approvalEligible: false,
      blocked: true,
    });
    expect(getRightsGateState(unverified)).toMatchObject({
      complete: false,
      approvalEligible: false,
      blocked: true,
    });
  });
});
