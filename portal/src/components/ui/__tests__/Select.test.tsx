import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { Select } from "../Select";

const options = [
  { value: "a", label: "Option A" },
  { value: "b", label: "Option B" },
];

describe("Select", () => {
  it("renders label and options", () => {
    render(<Select label="My Label" options={options} value="a" onChange={vi.fn()} />);
    expect(screen.getByLabelText("My Label")).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Option A" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Option B" })).toBeInTheDocument();
  });

  it("renders placeholder option", () => {
    render(<Select options={options} value="" onChange={vi.fn()} placeholder="Pick one" />);
    expect(screen.getByRole("option", { name: "Pick one" })).toBeInTheDocument();
  });

  it("calls onChange with selected value", () => {
    const onChange = vi.fn();
    render(<Select options={options} value="a" onChange={onChange} />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "b" } });
    expect(onChange).toHaveBeenCalledWith("b");
  });

  it("shows error message", () => {
    render(<Select label="Status" options={options} value="" onChange={vi.fn()} error="Required field" />);
    expect(screen.getByRole("alert")).toHaveTextContent("Required field");
  });

  it("sets aria-invalid when error is present", () => {
    render(<Select label="Status" options={options} value="" onChange={vi.fn()} error="Bad" />);
    expect(screen.getByRole("combobox")).toHaveAttribute("aria-invalid", "true");
  });
});
