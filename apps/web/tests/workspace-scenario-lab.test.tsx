import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { comparisonFixture } from "./fixtures/comparison";

const { runScenarioComparison } = vi.hoisted(() => ({ runScenarioComparison: vi.fn() }));
vi.mock("../lib/api/simulation", async () => {
  const actual = await vi.importActual<typeof import("../lib/api/simulation")>("../lib/api/simulation");
  return { ...actual, checkSimulationHealth: vi.fn().mockResolvedValue(true), runScenarioComparison };
});

import { Workspace } from "../app/workspace/workspace";

describe("Scenario Lab workspace", () => {
  beforeEach(() => { runScenarioComparison.mockReset(); runScenarioComparison.mockResolvedValue(comparisonFixture); });

  it("exposes labelled baseline, scenario, guardrail, and execution controls", async () => {
    render(<Workspace />);
    expect(screen.getByRole("heading", { name: "Current operation" })).toBeInTheDocument();
    expect(screen.getByLabelText("Ticket arrival interval")).toHaveAccessibleDescription(/new ticket arrives/i);
    expect(screen.getByRole("heading", { name: "What would you like to compare?" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "The situation" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Run comparison" })).toBeEnabled());
  });

  it("renames, duplicates, orders, and deletes with explicit keyboard actions", async () => {
    const user = userEvent.setup(); render(<Workspace />); await user.click(screen.getByRole("button", { name: "Advanced" }));
    const firstName = screen.getByLabelText("Scenario name", { selector: "#scenario-1-name" });
    await user.clear(firstName); await user.type(firstName, "Staffing trial");
    expect(screen.getByRole("heading", { name: "Staffing trial" })).toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: "Duplicate" })[0]);
    expect(screen.getByRole("heading", { name: "Staffing trial copy" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Move Staffing trial copy up" }));
    expect(screen.getAllByText(/Ready to compare/).length).toBeGreaterThanOrEqual(3);
    await user.click(screen.getAllByRole("button", { name: "Delete" })[0]);
    expect(screen.getAllByText(/Ready to compare/).length).toBeGreaterThanOrEqual(2);
  });

  it("defaults to a valid no-edit guided comparison and reveals Advanced controls on request", async () => {
    const user = userEvent.setup(); render(<Workspace />);
    expect(screen.getByRole("button", { name: "Guided" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("heading", { name: "Add one Level 1 agent" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Run comparison" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Run comparison" }));
    expect(runScenarioComparison.mock.calls[0][0]).toMatchObject({ objective: { metric: "averageCycleTime", direction: "minimize" }, execution: { runCount: 50 } });
    await user.click(screen.getByRole("button", { name: "Advanced" }));
    expect(screen.getByRole("group", { name: "Optional guardrail" })).toBeInTheDocument();
  });

  it("renders the result before deeper evidence, with uncertainty, disclaimer, navigation, orientation and glossary", async () => {
    const user = userEvent.setup(); render(<Workspace />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Run comparison" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Run comparison" }));
    expect(await screen.findByRole("heading", { name: "Comparison complete" })).toBeInTheDocument();
    expect(screen.getByText(/This is comparative simulation evidence, not a recommendation/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "See where the process changed" })).toBeInTheDocument();
    expect(screen.getAllByText(/Plausible range of the average change/i).length).toBeGreaterThan(0);
    await user.click(screen.getByRole("button", { name: "Skip orientation" }));
    expect(screen.queryByRole("button", { name: "Skip orientation" })).not.toBeInTheDocument();
    await user.click(screen.getByText("Terminology help"));
    expect(screen.getByText(/One selected sampled run used to explain timing/i)).toBeInTheDocument();
  });

  it("omits a disabled guardrail and maps an enabled threshold", async () => {
    const user = userEvent.setup(); render(<Workspace />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Run comparison" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Run comparison" }));
    expect(runScenarioComparison.mock.calls[0][0].guardrails).toEqual([]);
    await user.click(screen.getByRole("checkbox", { name: /check one required condition/i }));
    await user.click(screen.getByRole("button", { name: "Run comparison" }));
    expect(runScenarioComparison.mock.calls[1][0].guardrails).toEqual([{ metric: "slaAttainment", operator: "greaterThanOrEqual", value: 0.75 }]);
  });

  it("renders factual overview and keyboard-operable analysis tabs in Advanced mode", async () => {
    const user = userEvent.setup(); render(<Workspace />); await user.click(screen.getByRole("button", { name: "Advanced" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Run paired comparison" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Run paired comparison" }));
    expect(await screen.findByRole("heading", { name: "First in the returned observed ranking" })).toBeInTheDocument();
    const overview = screen.getByRole("tab", { name: "Overview" }); overview.focus(); await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Metrics" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("table", { name: /service metric comparison/i })).toBeInTheDocument();
  });

  it("renders confidence, probability, risk, resource, and textual status evidence in Advanced mode", async () => {
    const user = userEvent.setup(); render(<Workspace />); await user.click(screen.getByRole("button", { name: "Advanced" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Run paired comparison" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Run paired comparison" }));
    expect(await screen.findByLabelText(/paired mean confidence interval/i)).toHaveTextContent(/lower.*mean.*upper/i);
    expect(screen.getByLabelText(/improved 80.0%.*degraded 10.0%.*tied 10.0%/i)).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Risk" }));
    expect(screen.getByRole("group", { name: /paired transition counts/i })).toHaveTextContent(/Violation to compliance/);
    await user.click(screen.getByRole("tab", { name: "Resources" }));
    expect(screen.getAllByText("Baseline utilization").length).toBeGreaterThan(0);
    expect(screen.getByText("Higher utilization is not interpreted as automatically better or worse.")).toBeInTheDocument();
  });

  it("invalidates stale evidence after a scenario edit", async () => {
    const user = userEvent.setup(); render(<Workspace />); await user.click(screen.getByRole("button", { name: "Advanced" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Run paired comparison" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Run paired comparison" }));
    expect(await screen.findByRole("heading", { name: "Analysis" })).toBeInTheDocument();
    await user.type(screen.getByLabelText("Scenario name", { selector: "#scenario-1-name" }), " revised");
    expect(screen.queryByRole("heading", { name: "Analysis" })).not.toBeInTheDocument();
  });

  it("keeps generated product output free of prescriptive language", async () => {
    const user = userEvent.setup(); const { container } = render(<Workspace />); await user.click(screen.getByRole("button", { name: "Advanced" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Run paired comparison" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Run paired comparison" }));
    await screen.findByRole("heading", { name: "Analysis" });
    expect(container.textContent).not.toMatch(/recommended option|best action|optimal|winning scenario|you should/i);
  });

  it("uses accessible table headers and explicit export actions", async () => {
    const user = userEvent.setup(); render(<Workspace />); await user.click(screen.getByRole("button", { name: "Advanced" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Run paired comparison" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Run paired comparison" }));
    await user.click(screen.getByRole("tab", { name: "Metrics" }));
    const table = screen.getByRole("table", { name: /metric comparison/i });
    expect(within(table).getAllByRole("columnheader").length).toBeGreaterThan(6);
    expect(screen.getByRole("button", { name: "Export JSON" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Export CSV" })).toBeEnabled();
  });
});
