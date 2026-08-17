/**
 * The smallest API contract the review studio needs in M00.
 *
 * The page intentionally renders this contract as an offline-safe example. A
 * runtime request belongs to the API integration milestone and must not make
 * `next build` or ordinary tests depend on a running service.
 */
export const API_HEALTH_ENDPOINT = "/api/health" as const;

export interface ApiHealthResponse {
  status: "ok";
}

export const API_HEALTH_RESPONSE_EXAMPLE: ApiHealthResponse = Object.freeze({
  status: "ok",
});

export function isApiHealthResponse(value: unknown): value is ApiHealthResponse {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  return "status" in value && value.status === "ok";
}
