import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SensitivityPanel } from "../components/sensitivity/sensitivity-panel";
import { DEFAULT_FORM } from "../lib/templates/support";

describe("sensitivity panel", () => {
  it("shows explicit defaults, estimated work, and an always-visible result table region", () => {
    render(<SensitivityPanel baseline={{ ...DEFAULT_FORM }} health="ready" />);

    expect(screen.getByRole("heading", { name: "Sensitivity" })).toBeInTheDocument();
    expect(screen.getByLabelText("Tested values")).toHaveValue("2, 3, 4, 5");
    expect(screen.getByLabelText("Sensitivity runs")).toHaveValue("50");
    expect(screen.getByText(/20,000 work units/i)).toBeInTheDocument();
    expect(screen.getByRole("table", { name: /sensitivity response values/i })).toBeInTheDocument();
  });

  it("uses business-first labels in Guided mode", () => {
    render(<SensitivityPanel baseline={{ ...DEFAULT_FORM }} health="ready" guided />);

    expect(screen.getByRole("heading", { name: "Test different assumptions" })).toBeInTheDocument();
    expect(screen.getByLabelText("Type of assumption")).toBeInTheDocument();
    expect(screen.getByText("Did the result move consistently?")).toBeInTheDocument();
    expect(screen.getByText(/Shows how responsive the selected result/i)).toBeInTheDocument();
  });
});
