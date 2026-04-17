import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("@/lib/api-client", () => ({
  postAPI: vi.fn(),
}));

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, refresh: vi.fn() }),
}));

import { postAPI } from "@/lib/api-client";
import { SampleDataCta } from "@/components/upload/sample-data-cta";

const mockedPost = postAPI as unknown as Mock;

describe("SampleDataCta", () => {
  beforeEach(() => {
    mockedPost.mockReset();
    pushMock.mockReset();
  });

  it("renders a button with clear pharma-first copy", () => {
    render(<SampleDataCta />);
    expect(
      screen.getByRole("button", { name: /use sample pharma data/i }),
    ).toBeInTheDocument();
  });

  it("on click: calls the onboarding/load-sample endpoint", async () => {
    mockedPost.mockResolvedValue({
      rows_loaded: 5000,
      pipeline_run_id: "run-1",
      duration_seconds: 4.2,
    });

    render(<SampleDataCta />);
    const button = screen.getByRole("button", { name: /use sample pharma data/i });
    await userEvent.click(button);

    await waitFor(() => expect(mockedPost).toHaveBeenCalledTimes(1));
    expect(mockedPost).toHaveBeenCalledWith("/api/v1/onboarding/load-sample");
  });

  it("on success: redirects to /dashboard?first_upload=1", async () => {
    mockedPost.mockResolvedValue({
      rows_loaded: 5000,
      pipeline_run_id: "run-1",
      duration_seconds: 4.2,
    });

    render(<SampleDataCta />);
    await userEvent.click(
      screen.getByRole("button", { name: /use sample pharma data/i }),
    );

    await waitFor(() =>
      expect(pushMock).toHaveBeenCalledWith("/dashboard?first_upload=1"),
    );
  });

  it("shows a loading state while the request is in flight", async () => {
    let resolveFn: (v: unknown) => void = () => {};
    mockedPost.mockReturnValue(new Promise((r) => (resolveFn = r)));

    render(<SampleDataCta />);
    const button = screen.getByRole("button", { name: /use sample pharma data/i });
    await userEvent.click(button);

    // Button should show loading copy AND be disabled so double-click is impossible.
    expect(button).toBeDisabled();
    expect(button).toHaveTextContent(/loading sample|seeding|preparing/i);

    resolveFn({ rows_loaded: 5000, pipeline_run_id: "run-1", duration_seconds: 1 });
  });

  it("on failure: surfaces an inline error and does not redirect", async () => {
    mockedPost.mockRejectedValue(new Error("boom"));

    render(<SampleDataCta />);
    await userEvent.click(
      screen.getByRole("button", { name: /use sample pharma data/i }),
    );

    await waitFor(() =>
      expect(
        screen.getByText(/could not load sample data/i),
      ).toBeInTheDocument(),
    );
    expect(pushMock).not.toHaveBeenCalled();
  });
});
