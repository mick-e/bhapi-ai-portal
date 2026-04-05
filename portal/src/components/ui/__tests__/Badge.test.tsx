import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Badge } from "../Badge";

describe("Badge", () => {
  it("renders children text", () => {
    render(<Badge>Active</Badge>);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("applies neutral styles by default", () => {
    render(<Badge>Neutral</Badge>);
    expect(screen.getByText("Neutral").className).toContain("bg-gray-50");
    expect(screen.getByText("Neutral").className).toContain("text-gray-700");
  });

  it("applies success styles", () => {
    render(<Badge variant="success">OK</Badge>);
    expect(screen.getByText("OK").className).toContain("bg-green-50");
    expect(screen.getByText("OK").className).toContain("text-green-700");
  });

  it("applies error styles", () => {
    render(<Badge variant="error">Failed</Badge>);
    expect(screen.getByText("Failed").className).toContain("bg-red-50");
    expect(screen.getByText("Failed").className).toContain("text-red-700");
  });

  it("applies warning styles", () => {
    render(<Badge variant="warning">Warning</Badge>);
    expect(screen.getByText("Warning").className).toContain("bg-amber-50");
  });

  it("applies info styles", () => {
    render(<Badge variant="info">Info</Badge>);
    expect(screen.getByText("Info").className).toContain("bg-blue-50");
    expect(screen.getByText("Info").className).toContain("text-blue-700");
  });

  it("merges custom className", () => {
    render(<Badge className="ml-2">Tag</Badge>);
    expect(screen.getByText("Tag").className).toContain("ml-2");
  });
});
