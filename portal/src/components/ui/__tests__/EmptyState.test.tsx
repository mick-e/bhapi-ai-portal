import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { EmptyState } from "../EmptyState";

describe("EmptyState", () => {
  it("renders title and message", () => {
    render(<EmptyState title="No data" message="Nothing to show here." />);
    expect(screen.getByText("No data")).toBeInTheDocument();
    expect(screen.getByText("Nothing to show here.")).toBeInTheDocument();
  });

  it("renders action button when actionLabel and onAction are provided", () => {
    const onAction = vi.fn();
    render(<EmptyState title="Empty" message="Add something." actionLabel="Add Item" onAction={onAction} />);
    const btn = screen.getByRole("button", { name: "Add Item" });
    expect(btn).toBeInTheDocument();
    fireEvent.click(btn);
    expect(onAction).toHaveBeenCalledOnce();
  });

  it("does not render action button when actionLabel is missing", () => {
    render(<EmptyState title="Empty" message="Nothing here." />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("renders icon when provided", () => {
    render(
      <EmptyState
        title="Empty"
        message="Nothing."
        icon={<svg data-testid="test-icon" />}
      />
    );
    expect(screen.getByTestId("test-icon")).toBeInTheDocument();
  });

  it("does not render icon container when icon is not provided", () => {
    render(<EmptyState title="Empty" message="Nothing." />);
    expect(screen.queryByTestId("test-icon")).not.toBeInTheDocument();
  });
});
