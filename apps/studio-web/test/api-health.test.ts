import { describe, expect, it } from "vitest";

import {
  API_HEALTH_ENDPOINT,
  API_HEALTH_RESPONSE_EXAMPLE,
  isApiHealthResponse,
} from "../src/api-health";

describe("M00 API health contract", () => {
  it("keeps the endpoint and offline example stable", () => {
    expect(API_HEALTH_ENDPOINT).toBe("/api/health");
    expect(API_HEALTH_RESPONSE_EXAMPLE).toEqual({ status: "ok" });
  });

  it("accepts the minimum healthy response and rejects unrelated payloads", () => {
    expect(isApiHealthResponse({ status: "ok" })).toBe(true);
    expect(isApiHealthResponse({ status: "degraded" })).toBe(false);
    expect(isApiHealthResponse(null)).toBe(false);
    expect(isApiHealthResponse("ok")).toBe(false);
  });
});
