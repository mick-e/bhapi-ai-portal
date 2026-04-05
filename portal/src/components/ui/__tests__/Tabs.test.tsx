import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { Tabs } from "../Tabs";

const tabs = [
  { key: "overview", label: "Overview" },
  { key: "activity", label: "Activity", count: 5 },
  { key: "settings", label: "Settings" },
];

describe("Tabs", () => {
  it("renders all tab labels", () => {
    render(<Tabs tabs={tabs} active="overview" onChange={vi.fn()} />);
    expect(screen.getByRole("tab", { name: /Overview/ })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Activity/ })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Settings/ })).toBeInTheDocument();
  });

  it("marks the active tab with aria-selected=true", () => {
    render(<Tabs tabs={tabs} active="activity" onChange={vi.fn()} />);
    expect(screen.getByRole("tab", { name: /Activity/ })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: /Overview/ })).toHaveAttribute("aria-selected", "false");
  });

  it("calls onChange with the correct key on click", () => {
    const onChange = vi.fn();
    render(<Tabs tabs={tabs} active="overview" onChange={onChange} />);
    fireEvent.click(screen.getByRole("tab", { name: /Settings/ }));
    expect(onChange).toHaveBeenCalledWith("settings");
  });

  it("renders count badge when count is provided", () => {
    render(<Tabs tabs={tabs} active="overview" onChange={vi.fn()} />);
    expect(screen.getByText("5")).toBeInTheDocument();
  });

  it("has tablist role on container", () => {
    render(<Tabs tabs={tabs} active="overview" onChange={vi.fn()} />);
    expect(screen.getByRole("tablist")).toBeInTheDocument();
  });
});
