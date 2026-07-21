import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { resolveInitialMode } from "../app/workspace/page";

vi.mock("../lib/api/simulation", async () => {
  const actual = await vi.importActual<typeof import("../lib/api/simulation")>("../lib/api/simulation");
  return { ...actual, checkSimulationHealth: vi.fn().mockResolvedValue(true) };
});

import { Workspace } from "../app/workspace/workspace";
import Home from "../app/page";

describe("resolveInitialMode", () => {
  it("defaults to guided when no mode parameter is present", () => {
    expect(resolveInitialMode(undefined)).toBe("guided");
  });

  it("resolves an explicit guided parameter", () => {
    expect(resolveInitialMode("guided")).toBe("guided");
  });

  it("resolves an explicit advanced parameter", () => {
    expect(resolveInitialMode("advanced")).toBe("advanced");
  });

  it("defaults to guided for an invalid parameter", () => {
    expect(resolveInitialMode("not-a-mode")).toBe("guided");
  });

  it("uses the first value when the parameter is repeated", () => {
    expect(resolveInitialMode(["advanced", "guided"])).toBe("advanced");
  });
});

describe("Workspace initial presentation mode", () => {
  it("opens Guided by default", () => {
    render(<Workspace />);
    expect(screen.getByRole("button", { name: "Guided" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Advanced" })).toHaveAttribute("aria-pressed", "false");
  });

  it("opens Advanced when initialMode is advanced, preserved from the URL", () => {
    render(<Workspace initialMode="advanced" />);
    expect(screen.getByRole("button", { name: "Advanced" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("group", { name: "Optional guardrail" })).toBeInTheDocument();
  });

  it("still supports switching mode client-side after initializing as Advanced", async () => {
    const user = userEvent.setup(); render(<Workspace initialMode="advanced" />);
    await user.click(screen.getByRole("button", { name: "Guided" }));
    expect(screen.getByRole("button", { name: "Guided" })).toHaveAttribute("aria-pressed", "true");
  });
});

describe("Landing page action destinations", () => {
  it("routes the guided action to /workspace and the advanced action to /workspace?mode=advanced", () => {
    render(<Home />);
    expect(screen.getByRole("link", { name: /Try the guided comparison/i })).toHaveAttribute("href", "/workspace");
    expect(screen.getByRole("link", { name: "Open advanced workspace" })).toHaveAttribute("href", "/workspace?mode=advanced");
  });
});
