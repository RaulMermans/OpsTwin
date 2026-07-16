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
    expect(screen.getByRole("heading", { name: "Baseline" })).toBeInTheDocument();
    expect(screen.getByLabelText("Mean arrival interval")).toHaveAccessibleDescription(/minutes/i);
    expect(screen.getByRole("heading", { name: "Scenario set" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Optional guardrail" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Run paired comparison" })).toBeEnabled());
  });

  it("renames, duplicates, orders, and deletes with explicit keyboard actions", async () => {
    const user = userEvent.setup(); render(<Workspace />);
    const firstName = screen.getByLabelText("Scenario name", { selector: "#scenario-1-name" });
    await user.clear(firstName); await user.type(firstName, "Staffing trial");
    expect(screen.getByRole("heading", { name: "Staffing trial" })).toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: "Duplicate" })[0]);
    expect(screen.getByRole("heading", { name: "Staffing trial copy" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Move Staffing trial copy up" }));
    expect(screen.getAllByText(/Ready to compare/)).toHaveLength(3);
    await user.click(screen.getAllByRole("button", { name: "Delete" })[0]);
    expect(screen.getAllByText(/Ready to compare/)).toHaveLength(2);
  });

  it("omits a disabled guardrail and maps an enabled threshold", async () => {
    const user = userEvent.setup(); render(<Workspace />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Run paired comparison" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Run paired comparison" }));
    expect(runScenarioComparison.mock.calls[0][0].guardrails).toEqual([]);
    await user.click(screen.getByRole("checkbox", { name: /evaluate one eligibility guardrail/i }));
    await user.click(screen.getByRole("button", { name: "Run paired comparison" }));
    expect(runScenarioComparison.mock.calls[1][0].guardrails).toEqual([{ metric: "slaAttainment", operator: "greaterThanOrEqual", value: 0.75 }]);
  });

  it("renders factual overview and keyboard-operable analysis tabs", async () => {
    const user = userEvent.setup(); render(<Workspace />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Run paired comparison" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Run paired comparison" }));
    expect(await screen.findByRole("heading", { name: "Ranked first under the selected objective" })).toBeInTheDocument();
    const overview = screen.getByRole("tab", { name: "Overview" }); overview.focus(); await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Metrics" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("table", { name: /service metric comparison/i })).toBeInTheDocument();
  });

  it("renders confidence, probability, risk, resource, and textual status evidence", async () => {
    const user = userEvent.setup(); render(<Workspace />);
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
    const user = userEvent.setup(); render(<Workspace />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Run paired comparison" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Run paired comparison" }));
    expect(await screen.findByRole("heading", { name: "Analysis" })).toBeInTheDocument();
    await user.type(screen.getByLabelText("Scenario name", { selector: "#scenario-1-name" }), " revised");
    expect(screen.queryByRole("heading", { name: "Analysis" })).not.toBeInTheDocument();
  });

  it("keeps generated product output free of prescriptive language", async () => {
    const user = userEvent.setup(); const { container } = render(<Workspace />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Run paired comparison" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Run paired comparison" }));
    await screen.findByRole("heading", { name: "Analysis" });
    expect(container.textContent).not.toMatch(/recommended|recommendation|best action|optimal|winning scenario|you should/i);
  });

  it("uses accessible table headers and explicit export actions", async () => {
    const user = userEvent.setup(); render(<Workspace />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Run paired comparison" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Run paired comparison" }));
    await user.click(screen.getByRole("tab", { name: "Metrics" }));
    const table = screen.getByRole("table", { name: /metric comparison/i });
    expect(within(table).getAllByRole("columnheader").length).toBeGreaterThan(6);
    expect(screen.getByRole("button", { name: "Export JSON" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Export CSV" })).toBeEnabled();
  });
});
