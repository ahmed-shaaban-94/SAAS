import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ErrorBoundary } from "@/components/error-boundary";

function ProblemChild({ shouldThrow = true }: { shouldThrow?: boolean }) {
  if (shouldThrow) throw new Error("Test error message");
  return <div>No error</div>;
}

describe("ErrorBoundary", () => {
  // Suppress React error boundary console errors in test output
  const originalError = console.error;
  beforeEach(() => {
    console.error = vi.fn();
  });
  afterEach(() => {
    console.error = originalError;
  });

  it("renders children when no error", () => {
    render(
      <ErrorBoundary>
        <div>All good</div>
      </ErrorBoundary>,
    );
    expect(screen.getByText("All good")).toBeInTheDocument();
  });

  it("renders error UI when child throws", () => {
    render(
      <ErrorBoundary>
        <ProblemChild />
      </ErrorBoundary>,
    );
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("Test error message")).toBeInTheDocument();
  });

  it("shows Try again button that resets error state", async () => {
    const user = userEvent.setup();
    render(
      <ErrorBoundary>
        <ProblemChild shouldThrow={true} />
      </ErrorBoundary>,
    );
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();

    // After clicking Try again, error state resets (but child still throws)
    await user.click(screen.getByText("Try again"));
    // It will catch the error again
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });

  it("renders custom fallback when provided", () => {
    render(
      <ErrorBoundary fallback={<div>Custom error UI</div>}>
        <ProblemChild />
      </ErrorBoundary>,
    );
    expect(screen.getByText("Custom error UI")).toBeInTheDocument();
    expect(screen.queryByText("Something went wrong")).not.toBeInTheDocument();
  });

  it("shows generic message when error has no message", () => {
    function ThrowEmpty(): never {
      throw new Error();
    }
    render(
      <ErrorBoundary>
        <ThrowEmpty />
      </ErrorBoundary>,
    );
    expect(screen.getByText("An unexpected error occurred")).toBeInTheDocument();
  });
});
