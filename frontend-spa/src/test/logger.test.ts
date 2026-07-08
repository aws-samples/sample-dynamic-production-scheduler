import { describe, it, expect, vi } from "vitest";
import { logger } from "@/lib/logger";

describe("logger", () => {
  it("warn writes to console.warn", () => {
    const spy = vi.spyOn(console, "warn").mockImplementation(() => {});
    logger.warn("Test", "warning message");
    expect(spy).toHaveBeenCalledWith("[Test] warning message");
    spy.mockRestore();
  });

  it("error writes to console.error", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    logger.error("Test", "error message");
    expect(spy).toHaveBeenCalledWith("[Test] error message", "");
    spy.mockRestore();
  });

  it("error passes error object", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    const err = new Error("boom");
    logger.error("Test", "failed", err);
    expect(spy).toHaveBeenCalledWith("[Test] failed", err);
    spy.mockRestore();
  });
});
