import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { WorkflowVisualization } from "../components/workflow/workflow-map";
import { DEFAULT_FORM, buildBaseline } from "../lib/templates/support";
import type { ScenarioDraft } from "../lib/scenarios/builders";
import { comparisonFixture } from "./fixtures/comparison";
import { mapScenarioChanges } from "../lib/workflow/scenario-changes";
import type { WorkflowOperationalModel } from "../lib/workflow/presentation-model";

const scenarios: ScenarioDraft[] = [{ id: "scenario-1", name: "Add one Level 1 agent", type: "level1Staffing", value: 1 }];
const renderFlow = (result: typeof comparisonFixture | null = null) => render(<WorkflowVisualization model={buildBaseline({ ...DEFAULT_FORM })} baseline={DEFAULT_FORM} scenarios={scenarios} result={result} />);

describe("workflow visualization", () => {
  it("shows structure and semantic relationships before execution", () => {
    renderFlow();
    expect(screen.getByRole("heading", { name: "Flow" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Incoming tickets, source/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Quality check, stage/i })).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Workflow relationships" })).toHaveTextContent(/Quality check.*Level 2.*rework/i);
  });

  it("shows explicit scenario changes before execution", async () => {
    const user = userEvent.setup(); renderFlow();
    await user.click(screen.getByRole("button", { name: "Scenario changes" }));
    expect(screen.getByText("Capacity: 4 → 5")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Level 1 agents, resource.*changed/i })).toBeInTheDocument();
    expect(document.querySelector(".workflow-content")).toHaveClass("has-changes");
  });

  it("keeps result-dependent modes unavailable without evidence", () => {
    renderFlow();
    expect(screen.getByRole("button", { name: "Operational pressure" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Baseline vs scenario" })).toBeDisabled();
  });

  it("selects a stage and closes its inspector", async () => {
    const user = userEvent.setup(); renderFlow();
    const node = screen.getByRole("button", { name: /Triage, stage/i });
    await user.click(node);
    const inspector = screen.getByRole("complementary", { name: "Triage evidence" });
    expect(inspector).toHaveTextContent(/Triage team/);
    await user.click(within(inspector).getByRole("button", { name: "Close inspector" }));
    expect(screen.queryByRole("complementary", { name: "Triage evidence" })).not.toBeInTheDocument();
    expect(node).toHaveFocus();
  });

  it("keeps a rendered map canvas meaningful when the inspector is open", async () => {
    const user = userEvent.setup(); const { container } = renderFlow();
    const canvas = container.querySelector<HTMLElement>(".workflow-canvas");
    expect(canvas).not.toBeNull();
    Object.defineProperty(canvas!, "getBoundingClientRect", { configurable: true, value: () => ({ width: 640, height: 600 }) });
    await user.click(screen.getByRole("button", { name: /Incoming tickets, source/i }));
    expect(container.querySelector(".workflow-content")).toHaveClass("has-inspector");
    expect(canvas!.getBoundingClientRect().width).toBeGreaterThanOrEqual(640);
  });

  it("renders returned pressure values and relative-intensity label", async () => {
    const user = userEvent.setup(); renderFlow(comparisonFixture);
    await user.click(screen.getByRole("button", { name: "Operational pressure" }));
    expect(screen.getByText("Relative intensity within the current result")).toBeInTheDocument();
    expect(screen.getByLabelText(/Triage.*Observed waiting/i)).toHaveTextContent("4.00");
  });

  it("renders supplied baseline, scenario, and resource delta evidence", async () => {
    const user = userEvent.setup(); renderFlow(comparisonFixture);
    await user.click(screen.getByRole("button", { name: "Baseline vs scenario" }));
    await user.click(screen.getByRole("button", { name: /Level 1 agents, resource/i }));
    const inspector = screen.getByRole("complementary", { name: "Level 1 agents evidence" });
    expect(inspector).toHaveTextContent(/70.0%/);
    expect(inspector).toHaveTextContent(/62.0%/);
    expect(inspector).toHaveTextContent(/-8.0 pp/);
  });

  it("provides a visible list mode and avoids restricted product language", async () => {
    const user = userEvent.setup(); const { container } = renderFlow(comparisonFixture);
    await user.click(screen.getByRole("button", { name: "View as list" }));
    expect(screen.getByRole("region", { name: "Workflow list view" })).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/recommended|recommendation|best action|optimal|winning scenario|you should|root cause|definitive bottleneck/i);
  });
});

describe("workflow scenario change mapping", () => {
  const model = buildBaseline({ ...DEFAULT_FORM }) as WorkflowOperationalModel;

  it("maps the backend route target to exactly one visual edge", () => {
    const mapped = mapScenarioChanges(model, {
      id: "route-change",
      name: "Escalation route",
      overrides: [{ entityType: "route", entityId: "triage-routing:level-2", field: "probability", operation: "replace", value: 0.3 }],
    });

    expect(mapped.warnings).toEqual([]);
    expect(mapped.changes[0]).toMatchObject({ baselineValue: 0.2, targetIds: ["route:triage-routing:1"] });
  });

  it("resolves fixed source intervals and maximum rework attempts", () => {
    const fixedModel = structuredClone(model);
    fixedModel.sources[0].arrival = { type: "fixed", interval: 3 };
    const mapped = mapScenarioChanges(fixedModel, {
      id: "parameter-changes",
      name: "Parameter changes",
      overrides: [
        { entityType: "source", entityId: fixedModel.sources[0].id, field: "arrivalInterval", operation: "replace", value: 4 },
        { entityType: "stage", entityId: "quality-check", field: "maximumReworkAttempts", operation: "replace", value: 2 },
      ],
    });

    expect(mapped.changes.map((change) => change.baselineValue)).toEqual([3, 2]);
  });

  it("warns instead of mapping an unknown route option", () => {
    const mapped = mapScenarioChanges(model, {
      id: "bad-route",
      name: "Bad route",
      overrides: [{ entityType: "route", entityId: "triage-routing:missing", field: "probability", operation: "replace", value: 0.3 }],
    });

    expect(mapped.changes).toEqual([]);
    expect(mapped.warnings[0]).toMatch(/unknown route/i);
  });
});
