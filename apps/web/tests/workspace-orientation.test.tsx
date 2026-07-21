import { readFileSync } from "node:fs";
import { join } from "node:path";

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

vi.mock("../lib/api/simulation", async () => {
  const actual = await vi.importActual<typeof import("../lib/api/simulation")>("../lib/api/simulation");
  return { ...actual, checkSimulationHealth: vi.fn().mockResolvedValue(true) };
});

import { Workspace } from "../app/workspace/workspace";

describe("Guided first-run orientation", () => {
  it("is visible on initial render without reading browser storage", async () => {
    const sessionStorageSpy = vi.spyOn(window.sessionStorage, "getItem");
    render(<Workspace />);
    expect(screen.getByRole("button", { name: "Skip orientation" })).toBeInTheDocument();
    expect(sessionStorageSpy).not.toHaveBeenCalled();
    sessionStorageSpy.mockRestore();
  });

  it("dismisses by mouse click and stays dismissed for the mounted instance", async () => {
    const user = userEvent.setup(); render(<Workspace />);
    await user.click(screen.getByRole("button", { name: "Skip orientation" }));
    expect(screen.queryByRole("button", { name: "Skip orientation" })).not.toBeInTheDocument();
  });

  it("dismisses by keyboard activation", async () => {
    const user = userEvent.setup(); render(<Workspace />);
    screen.getByRole("button", { name: "Skip orientation" }).focus();
    await user.keyboard("{Enter}");
    expect(screen.queryByRole("button", { name: "Skip orientation" })).not.toBeInTheDocument();
  });

  it("shows the orientation again after a full remount (page reload), matching the documented reload behavior", async () => {
    const user = userEvent.setup(); const { unmount } = render(<Workspace />);
    await user.click(screen.getByRole("button", { name: "Skip orientation" }));
    expect(screen.queryByRole("button", { name: "Skip orientation" })).not.toBeInTheDocument();
    unmount();
    render(<Workspace />);
    expect(screen.getByRole("button", { name: "Skip orientation" })).toBeInTheDocument();
  });

  it("does not conceal a hydration mismatch with suppressHydrationWarning", () => {
    const source = readFileSync(join(process.cwd(), "app/workspace/workspace.tsx"), "utf8");
    expect(source).not.toMatch(/suppressHydrationWarning/);
  });
});
