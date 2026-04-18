import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LeadCaptureModal } from "@/components/marketing/lead-capture-modal";

const fetchMock = vi.fn();

describe("LeadCaptureModal", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the trigger button", () => {
    render(<LeadCaptureModal trigger="Request Pilot Access" />);
    expect(screen.getByRole("button", { name: /request pilot access/i })).toBeInTheDocument();
  });

  it("opens the dialog on trigger click", async () => {
    render(<LeadCaptureModal trigger="Request Pilot Access" />);
    await userEvent.click(screen.getByRole("button", { name: /request pilot access/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/company/i)).toBeInTheDocument();
  });

  it("submits the form and shows success state", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    } as Response);

    render(<LeadCaptureModal trigger="Request Pilot Access" />);
    await userEvent.click(screen.getByRole("button", { name: /request pilot access/i }));
    await userEvent.type(screen.getByLabelText(/email address/i), "pilot@example.com");
    await userEvent.type(screen.getByLabelText(/name/i), "Ahmed");
    await userEvent.type(screen.getByLabelText(/company/i), "DataPharma");
    await userEvent.click(screen.getByRole("button", { name: /submit request/i }));

    await waitFor(() =>
      expect(screen.getByText(/you're on the list/i)).toBeInTheDocument()
    );
  });

  it("shows error message on API failure", async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      json: async () => ({ message: "Server error" }),
    } as Response);

    render(<LeadCaptureModal trigger="Request Pilot Access" />);
    await userEvent.click(screen.getByRole("button", { name: /request pilot access/i }));
    await userEvent.type(screen.getByLabelText(/email address/i), "bad@example.com");
    await userEvent.click(screen.getByRole("button", { name: /submit request/i }));

    await waitFor(() =>
      expect(screen.getByText(/server error/i)).toBeInTheDocument()
    );
  });
});
