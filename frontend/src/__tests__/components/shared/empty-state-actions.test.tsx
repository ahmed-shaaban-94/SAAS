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
import {
  LoadSampleAction,
  UploadDataAction,
} from "@/components/shared/empty-state-actions";

const mockedPost = postAPI as unknown as Mock;

describe("LoadSampleAction", () => {
  beforeEach(() => {
    mockedPost.mockReset();
    pushMock.mockReset();
  });

  it("renders a button labelled 'Load sample data'", () => {
    render(<LoadSampleAction />);
    expect(
      screen.getByRole("button", { name: /load sample data/i }),
    ).toBeInTheDocument();
  });

  it("on click: calls /api/v1/onboarding/load-sample and redirects", async () => {
    mockedPost.mockResolvedValue({
      rows_loaded: 5000,
      pipeline_run_id: "run-1",
      duration_seconds: 4.2,
    });

    render(<LoadSampleAction />);
    await userEvent.click(
      screen.getByRole("button", { name: /load sample data/i }),
    );

    await waitFor(() => {
      expect(mockedPost).toHaveBeenCalledWith("/api/v1/onboarding/load-sample");
      expect(pushMock).toHaveBeenCalledWith("/dashboard?first_upload=1");
    });
  });

  it("is disabled while the request is in flight", async () => {
    let resolveFn: (v: unknown) => void = () => {};
    mockedPost.mockReturnValue(new Promise((r) => (resolveFn = r)));

    render(<LoadSampleAction />);
    const button = screen.getByRole("button", { name: /load sample data/i });
    await userEvent.click(button);
    expect(button).toBeDisabled();
    resolveFn({ rows_loaded: 5000, pipeline_run_id: "r", duration_seconds: 1 });
  });

  it("surfaces an inline error on failure", async () => {
    mockedPost.mockRejectedValue(new Error("nope"));
    render(<LoadSampleAction />);
    await userEvent.click(
      screen.getByRole("button", { name: /load sample data/i }),
    );
    await waitFor(() =>
      expect(
        screen.getByText(/could not load sample data/i),
      ).toBeInTheDocument(),
    );
    expect(pushMock).not.toHaveBeenCalled();
  });
});

describe("UploadDataAction", () => {
  it("renders a link to /upload", () => {
    render(<UploadDataAction />);
    const link = screen.getByRole("link", { name: /upload your data/i });
    expect(link).toHaveAttribute("href", "/upload");
  });

  it("accepts a custom label", () => {
    render(<UploadDataAction label="Bring your own file" />);
    expect(
      screen.getByRole("link", { name: /bring your own file/i }),
    ).toBeInTheDocument();
  });
});
