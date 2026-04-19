import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";

import { ConnectionPill } from "@/components/pos/shell/ConnectionPill";
import messages from "../../../../../messages/en.json";

function renderPill(props: React.ComponentProps<typeof ConnectionPill>) {
  return render(
    <NextIntlClientProvider locale="en" messages={messages}>
      <ConnectionPill {...props} />
    </NextIntlClientProvider>,
  );
}

describe("ConnectionPill", () => {
  it("renders 'Online' with the online variant when online=true", () => {
    renderPill({ online: true });
    const pill = screen.getByRole("status");
    expect(pill).toHaveAttribute("data-variant", "online");
    expect(pill).toHaveTextContent(/online/i);
  });

  it("renders 'Provisional — N queued' when offline with queueDepth > 0", () => {
    renderPill({ online: false, queueDepth: 5 });
    const pill = screen.getByRole("status");
    expect(pill).toHaveAttribute("data-variant", "provisional-queued");
    expect(pill).toHaveTextContent(/provisional\s*—\s*5 queued/i);
  });

  it("renders 'Provisional' when offline with queueDepth = 0", () => {
    renderPill({ online: false, queueDepth: 0 });
    const pill = screen.getByRole("status");
    expect(pill).toHaveAttribute("data-variant", "provisional");
    expect(pill).toHaveTextContent(/^provisional$/i);
  });

  it("defaults queueDepth to 0 when prop omitted", () => {
    renderPill({ online: false });
    const pill = screen.getByRole("status");
    expect(pill).toHaveAttribute("data-variant", "provisional");
  });

  it("treats online=true with residual queueDepth as Online (no amber)", () => {
    renderPill({ online: true, queueDepth: 7 });
    const pill = screen.getByRole("status");
    expect(pill).toHaveAttribute("data-variant", "online");
    expect(pill).toHaveTextContent(/online/i);
  });
});
