import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { comparisonFixture } from "./fixtures/comparison";

const { runScenarioComparison } = vi.hoisted(() => ({ runScenarioComparison: vi.fn() }));
vi.mock("../lib/api/simulation", async () => {
  const actual = await vi.importActual<typeof import("../lib/api/simulation")>("../lib/api/simulation");
  return { ...actual, checkSimulationHealth: vi.fn().mockResolvedValue(true), runScenarioComparison };
});

import { Workspace } from "../app/workspace/workspace";

describe("Guided evidence navigation", () => {
  beforeEach(() => { runScenarioComparison.mockReset(); runScenarioComparison.mockResolvedValue(comparisonFixture); });

  async function runComparison(user: ReturnType<typeof userEvent.setup>) {
    await waitFor(() => expect(screen.getByRole("button", { name: "Run comparison" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Run comparison" }));
    await screen.findByRole("heading", { name: "Comparison complete" });
  }

  it("defaults to the Result panel and explains prerequisites for panels that need a result", async () => {
    render(<Workspace />);
    const flowTab = screen.getByRole("tab", { name: "Process" });
    expect(screen.getByRole("tab", { name: "Result" })).toHaveAttribute("aria-selected", "true");
    expect(flowTab).toHaveAttribute("aria-selected", "false");
    expect(screen.getByText("Run the comparison to see the result.")).toBeVisible();
  });

  it("shows exactly one evidence panel at a time and hides the rest from the accessibility tree", async () => {
    const user = userEvent.setup(); render(<Workspace />); await runComparison(user);
    expect(screen.getByRole("heading", { name: "Comparison complete" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Process" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Process" }));
    expect(screen.getByRole("heading", { name: "Process" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Comparison complete" })).not.toBeInTheDocument();
  });

  it("moves the active panel with arrow-key navigation", async () => {
    const user = userEvent.setup(); render(<Workspace />); await runComparison(user);
    const summaryTab = screen.getByRole("tab", { name: "Result" });
    summaryTab.focus();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Process" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Process" })).toHaveFocus();
  });

  it("reaches plain-language evidence views through the Guided tabs without duplicating Advanced's tablist", async () => {
    const user = userEvent.setup(); render(<Workspace />); await runComparison(user);
    await user.click(screen.getByRole("tab", { name: "Uncertainty" }));
    expect(screen.getByRole("group", { name: /paired transition counts/i })).toBeVisible();
    await user.click(screen.getByRole("tab", { name: "Team workload" }));
    expect(screen.getByText("Higher utilization is not interpreted as automatically better or worse.")).toBeVisible();
    await user.click(screen.getByRole("tab", { name: "Technical details" }));
    expect(screen.getByText("Reproducible evidence")).toBeVisible();
    expect(screen.queryByRole("tablist", { name: "Analysis sections" })).not.toBeInTheDocument();
  });

  it("resets the Guided evidence view to Summary when the result becomes stale", async () => {
    const user = userEvent.setup(); render(<Workspace />); await runComparison(user);
    await user.click(screen.getByRole("tab", { name: "Process" }));
    expect(screen.getByRole("tab", { name: "Process" })).toHaveAttribute("aria-selected", "true");
    await user.type(screen.getByLabelText("Ticket arrival interval"), "1");
    expect(screen.getByRole("tab", { name: "Result" })).toHaveAttribute("aria-selected", "true");
  });

  it("navigates from the summary's evidence links directly to the corresponding Guided panel", async () => {
    const user = userEvent.setup(); render(<Workspace />); await runComparison(user);
    await user.click(screen.getByRole("button", { name: "Watch a representative run" }));
    expect(screen.getByRole("tab", { name: "Example run" })).toHaveAttribute("aria-selected", "true");
  });

  it("preserves Advanced mode's full detailed workspace unchanged", async () => {
    const user = userEvent.setup(); render(<Workspace />); await user.click(screen.getByRole("button", { name: "Advanced" }));
    expect(screen.queryByRole("tablist", { name: "Guided evidence sections" })).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Run paired comparison" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Run paired comparison" }));
    expect(await screen.findByRole("heading", { name: "Analysis" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Overview" })).toBeInTheDocument();
  });
});
