import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { EconomicsPanel } from "../components/economics/economics-panel";
import { DEFAULT_FORM } from "../lib/templates/support";

describe("economics panel", () => {
  it("renders explicit assumptions and separate intervention evidence controls", () => {
    render(<EconomicsPanel baseline={{ ...DEFAULT_FORM }} scenarios={[{ id: "scenario-1", name: "Capacity", type: "level1Staffing", value: 1 }]} runs={10} objective="averageCycleTime" health="ready" />);
    expect(screen.getByRole("heading", { name: "Economics" })).toBeInTheDocument();
    expect(screen.getByLabelText(/currency/i)).toHaveValue("EUR");
    expect(screen.getByLabelText(/one-time cost/i)).toBeInTheDocument();
    expect(screen.getByText(/does not infer costs or make a prescriptive/i)).toBeInTheDocument();
  });

  it("explains missing values in Guided mode", () => {
    render(<EconomicsPanel baseline={{ ...DEFAULT_FORM }} scenarios={[{ id: "scenario-1", name: "Capacity", type: "level1Staffing", value: 1 }]} runs={10} objective="averageCycleTime" health="ready" guided />);
    expect(screen.getByRole("heading", { name: "Costs" })).toBeInTheDocument();
    expect(screen.getByText(/will not treat a missing value as zero/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/General-support availability cost/i)).toBeInTheDocument();
  });

  it("shows a dynamic per-hour equivalent only for valid supplied rates", async () => {
    const user = userEvent.setup();
    render(<EconomicsPanel baseline={{ ...DEFAULT_FORM }} scenarios={[]} runs={10} objective="averageCycleTime" health="ready" guided />);
    const input = screen.getByLabelText(/General-support availability cost/i);
    const rateRow = input.parentElement?.parentElement;
    expect(rateRow).not.toBeNull();
    await user.type(input, "1");
    expect(within(rateRow!).getByText("Equivalent to EUR 60.00 per agent-hour")).toBeInTheDocument();
    await user.clear(input);
    await user.type(input, "0.5");
    expect(within(rateRow!).getByText("Equivalent to EUR 30.00 per agent-hour")).toBeInTheDocument();
    await user.clear(input);
    await waitFor(() => expect(within(rateRow!).queryByText(/Equivalent to EUR/)).not.toBeInTheDocument());
    await user.type(input, "invalid");
    await waitFor(() => expect(within(rateRow!).queryByText(/Equivalent to EUR/)).not.toBeInTheDocument());
  });
});
