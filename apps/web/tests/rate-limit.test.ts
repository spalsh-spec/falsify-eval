import { beforeEach, describe, expect, it } from "vitest";
import { rateLimit, resetRateLimits } from "../src/lib/rate-limit";

describe("rate limiter", () => {
  beforeEach(() => resetRateLimits());

  it("allows until the limit then blocks", () => {
    expect(rateLimit("k", 2, 1000, 0).allowed).toBe(true);
    expect(rateLimit("k", 2, 1000, 1).allowed).toBe(true);
    expect(rateLimit("k", 2, 1000, 2).allowed).toBe(false);
  });

  it("resets after the window", () => {
    expect(rateLimit("k", 1, 1000, 0).allowed).toBe(true);
    expect(rateLimit("k", 1, 1000, 1).allowed).toBe(false);
    expect(rateLimit("k", 1, 1000, 1001).allowed).toBe(true);
  });
});
