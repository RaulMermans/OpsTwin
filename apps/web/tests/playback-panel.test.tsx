import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { PlaybackPanel } from "../components/playback/playback-panel";
import { DEFAULT_FORM, buildBaseline } from "../lib/templates/support";
import type { ComparisonResult } from "../lib/api/simulation";

function rawEvent(overrides: Record<string, unknown>): Record<string, unknown> {
  return {
    simulationTime: 0, sequence: 0, eventType: "ITEM_CREATED", itemId: "item-1",
    stageId: null, resourcePoolId: null, routeId: null, targetId: null, sampledDuration: null,
    ...overrides,
  };
}

const events = [
  rawEvent({ sequence: 0, simulationTime: 0, eventType: "ITEM_CREATED", itemId: "item-1" }),
  rawEvent({ sequence: 1, simulationTime: 0, eventType: "QUEUE_ENTERED", itemId: "item-1", stageId: "triage" }),
  rawEvent({ sequence: 2, simulationTime: 2, eventType: "PROCESS_STARTED", itemId: "item-1", stageId: "triage", resourcePoolId: "level-1-agents" }),
  rawEvent({ sequence: 3, simulationTime: 10, eventType: "PROCESS_COMPLETED", itemId: "item-1", stageId: "triage" }),
  rawEvent({ sequence: 4, simulationTime: 10, eventType: "ITEM_COMPLETED", itemId: "item-1" }),
];

function representative(runIndex: number, seed: number) {
  return {
    variantId: "baseline",
    representative: {
      runIndex,
      seed,
      selectionMethod: "normalized_median_vector",
      distance: 0.1,
      detailMode: "sampled",
      includedEventCount: events.length,
      result: {
        observation: { measurementStart: 0, measurementEnd: 100, measurementDuration: 100 },
        resultDetail: { selectedItemIds: ["item-1"] },
        events,
      },
    },
  };
}

function makeResult(withScenario: boolean): ComparisonResult {
  return {
    schemaVersion: "0.5.0",
    baselineModelHash: "hash-baseline",
    requestedRunCount: 10,
    baseline: {},
    scenarios: withScenario ? [{ scenarioId: "scenario-1", scenarioName: "Faster triage", scenarioModelHash: "hash-scenario" }] : [],
    ranking: [],
    objective: { metric: "averageCycleTime" },
    workBudget: {},
    execution: {},
    integrity: { status: "passed", checksRun: 10 },
    representatives: {
      baseline: representative(3, 42),
      scenario: withScenario ? { ...representative(3, 42), variantId: "scenario-1" } : null,
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
  } as any;
}

describe("PlaybackPanel", () => {
  it("shows an unavailable state without a representative", () => {
    render(<PlaybackPanel result={null} model={buildBaseline({ ...DEFAULT_FORM })} />);
    expect(screen.getByText(/Representative playback is unavailable/)).toBeInTheDocument();
  });

  it("shows the fixed disclaimer and representative identity", () => {
    render(<PlaybackPanel result={makeResult(false)} model={buildBaseline({ ...DEFAULT_FORM })} />);
    expect(screen.getByText(/This playback illustrates one representative sampled run/)).toBeInTheDocument();
    expect(screen.getByText(/Run index 3/)).toBeInTheDocument();
    expect(screen.getByText(/seed 42/)).toBeInTheDocument();
  });

  it("disables the scenario toggle when no scenario representative was retained", () => {
    render(<PlaybackPanel result={makeResult(false)} model={buildBaseline({ ...DEFAULT_FORM })} />);
    expect(screen.getByRole("button", { name: /Selected scenario representative/ })).toBeDisabled();
  });

  it("discloses paired identity when baseline and scenario share a run index and seed", async () => {
    const user = userEvent.setup();
    render(<PlaybackPanel result={makeResult(true)} model={buildBaseline({ ...DEFAULT_FORM })} />);
    await user.click(screen.getByRole("button", { name: /Selected scenario representative/ }));
    expect(screen.getByText("Both playbacks use the same paired run index and seed.")).toBeInTheDocument();
  });

  it("renders the event ledger with a caption and current-row identification", () => {
    render(<PlaybackPanel result={makeResult(false)} model={buildBaseline({ ...DEFAULT_FORM })} />);
    expect(screen.getByText(/Ordered representative event ledger/)).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Time" })).toBeInTheDocument();
  });

  it("keeps the aggregate and playback evidence labels distinct and avoids restricted language", () => {
    const { container } = render(<PlaybackPanel result={makeResult(false)} model={buildBaseline({ ...DEFAULT_FORM })} />);
    expect(screen.getByText("Representative sampled-run evidence")).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/typical run|proves|root cause|recommended|best action|optimal|winning scenario|you should|guaranteed/i);
  });
});
