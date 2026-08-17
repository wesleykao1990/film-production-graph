import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

describe("studio smoke page", () => {
  it("declares the foundation UI without a network request", () => {
    const pagePath = fileURLToPath(new URL("../app/page.tsx", import.meta.url));
    const source = readFileSync(pagePath, "utf8");

    expect(source).toContain("Film Production Graph");
    expect(source).toContain("Foundation Lite review studio");
    expect(source).toContain("GET ${API_HEALTH_ENDPOINT}");
    expect(source).toContain("no API request is made during build or smoke");
    expect(source).not.toMatch(/\bfetch\s*\(/);
  });
});
