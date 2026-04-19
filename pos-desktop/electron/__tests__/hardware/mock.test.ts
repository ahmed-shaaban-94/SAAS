import type { ReceiptPayload } from "../../ipc/contracts";
import {
  MockPrinter,
  MockDrawer,
  takePrinterLog,
  takeDrawerLog,
  createMockHardware,
} from "../../hardware/mock";

// Minimal ReceiptPayload fixture
const receipt: ReceiptPayload = {
  storeName: "Test Pharmacy",
  storeAddress: "123 Main St",
  storePhone: "01000000000",
  logoPath: null,
  transactionId: 1,
  receiptNumber: "RCP-001",
  createdAt: "2026-01-01T12:00:00Z",
  staffName: "Ahmed",
  customerName: null,
  items: [
    {
      name: "Paracetamol",
      qty: "2",
      unitPrice: "5.00",
      lineTotal: "10.00",
      batch: null,
      expiry: null,
    },
  ],
  subtotal: "10.00",
  discount: "0.00",
  tax: "0.00",
  total: "10.00",
  paymentMethod: "cash",
  cashTendered: "10.00",
  changeDue: "0.00",
  languages: ["ar", "en"],
  currency: "EGP",
  confirmation: "provisional",
};

beforeEach(() => {
  // Drain stale log entries from module-level shared arrays
  takePrinterLog();
  takeDrawerLog();
});

describe("MockPrinter", () => {
  describe("print()", () => {
    it("succeeds when printer is healthy", async () => {
      const printer = new MockPrinter();
      const result = await printer.print(receipt);
      expect(result.success).toBe(true);
      expect(result.error).toBeUndefined();
    });

    it("fails with 'offline' when _setOnline(false)", async () => {
      const printer = new MockPrinter();
      printer._setOnline(false);
      const result = await printer.print(receipt);
      expect(result.success).toBe(false);
      expect(result.error).toBe("offline");
    });

    it("fails with 'cover_open' when _setCover('open')", async () => {
      const printer = new MockPrinter();
      printer._setCover("open");
      const result = await printer.print(receipt);
      expect(result.success).toBe(false);
      expect(result.error).toBe("cover_open");
    });

    it("fails with 'paper_out' when _setPaper('out')", async () => {
      const printer = new MockPrinter();
      printer._setPaper("out");
      const result = await printer.print(receipt);
      expect(result.success).toBe(false);
      expect(result.error).toBe("paper_out");
    });

    it("offline check takes priority over cover_open", async () => {
      const printer = new MockPrinter();
      printer._setOnline(false);
      printer._setCover("open");
      const result = await printer.print(receipt);
      expect(result.error).toBe("offline");
    });
  });

  describe("status()", () => {
    it("returns healthy defaults", async () => {
      const printer = new MockPrinter();
      const s = await printer.status();
      expect(s.online).toBe(true);
      expect(s.paper).toBe("ok");
      expect(s.cover).toBe("closed");
    });

    it("reflects _setOnline(false)", async () => {
      const printer = new MockPrinter();
      printer._setOnline(false);
      const s = await printer.status();
      expect(s.online).toBe(false);
    });

    it("reflects _setPaper('low')", async () => {
      const printer = new MockPrinter();
      printer._setPaper("low");
      const s = await printer.status();
      expect(s.paper).toBe("low");
    });

    it("reflects _setPaper('out')", async () => {
      const printer = new MockPrinter();
      printer._setPaper("out");
      const s = await printer.status();
      expect(s.paper).toBe("out");
    });

    it("reflects _setCover('open')", async () => {
      const printer = new MockPrinter();
      printer._setCover("open");
      const s = await printer.status();
      expect(s.cover).toBe("open");
    });
  });

  describe("testPrint()", () => {
    it("succeeds when printer is healthy", async () => {
      const printer = new MockPrinter();
      const result = await printer.testPrint();
      expect(result.success).toBe(true);
    });

    it("fails when offline", async () => {
      const printer = new MockPrinter();
      printer._setOnline(false);
      const result = await printer.testPrint();
      expect(result.success).toBe(false);
    });

    it("fails when paper is out", async () => {
      const printer = new MockPrinter();
      printer._setPaper("out");
      const result = await printer.testPrint();
      expect(result.success).toBe(false);
    });

    it("fails when cover is open", async () => {
      const printer = new MockPrinter();
      printer._setCover("open");
      const result = await printer.testPrint();
      expect(result.success).toBe(false);
    });

    it("succeeds with paper='low' (low paper is not a hard stop)", async () => {
      const printer = new MockPrinter();
      printer._setPaper("low");
      const result = await printer.testPrint();
      expect(result.success).toBe(true);
    });
  });
});

describe("MockDrawer", () => {
  describe("open()", () => {
    it("succeeds on a fresh instance", async () => {
      const drawer = new MockDrawer();
      const result = await drawer.open();
      expect(result.success).toBe(true);
    });

    it("fails N times after _injectFailures(N), then succeeds", async () => {
      const drawer = new MockDrawer();
      drawer._injectFailures(2);

      const first = await drawer.open();
      expect(first.success).toBe(false);

      const second = await drawer.open();
      expect(second.success).toBe(false);

      const third = await drawer.open();
      expect(third.success).toBe(true);
    });

    it("fails exactly once after _injectFailures(1)", async () => {
      const drawer = new MockDrawer();
      drawer._injectFailures(1);
      expect((await drawer.open()).success).toBe(false);
      expect((await drawer.open()).success).toBe(true);
    });
  });
});

describe("takePrinterLog / takeDrawerLog", () => {
  it("records print calls", async () => {
    const printer = new MockPrinter();
    await printer.print(receipt);
    const log = takePrinterLog();
    expect(log).toHaveLength(1);
    expect(log[0].kind).toBe("print");
    expect(log[0].payload).toEqual(receipt);
  });

  it("records status calls", async () => {
    const printer = new MockPrinter();
    await printer.status();
    const log = takePrinterLog();
    expect(log).toHaveLength(1);
    expect(log[0].kind).toBe("status");
  });

  it("records testPrint calls", async () => {
    const printer = new MockPrinter();
    await printer.testPrint();
    const log = takePrinterLog();
    expect(log).toHaveLength(1);
    expect(log[0].kind).toBe("testPrint");
  });

  it("clears the printer log after taking a snapshot", async () => {
    const printer = new MockPrinter();
    await printer.print(receipt);
    takePrinterLog(); // drains
    const second = takePrinterLog();
    expect(second).toHaveLength(0);
  });

  it("records drawer open calls", async () => {
    const drawer = new MockDrawer();
    await drawer.open();
    const log = takeDrawerLog();
    expect(log).toHaveLength(1);
    expect(log[0].kind).toBe("open");
  });

  it("clears the drawer log after taking a snapshot", async () => {
    const drawer = new MockDrawer();
    await drawer.open();
    takeDrawerLog(); // drains
    const second = takeDrawerLog();
    expect(second).toHaveLength(0);
  });

  it("accumulates multiple calls before draining", async () => {
    const printer = new MockPrinter();
    await printer.print(receipt);
    await printer.status();
    await printer.testPrint();
    const log = takePrinterLog();
    expect(log).toHaveLength(3);
    expect(log.map((e) => e.kind)).toEqual(["print", "status", "testPrint"]);
  });

  it("log entries have an 'at' ISO timestamp string", async () => {
    const printer = new MockPrinter();
    await printer.print(receipt);
    const log = takePrinterLog();
    expect(typeof log[0].at).toBe("string");
    expect(() => new Date(log[0].at)).not.toThrow();
  });
});

describe("createMockHardware", () => {
  it("returns a printer and a drawer", () => {
    const hw = createMockHardware();
    expect(hw.printer).toBeInstanceOf(MockPrinter);
    expect(hw.drawer).toBeInstanceOf(MockDrawer);
  });

  it("returns distinct instances on each call", () => {
    const hw1 = createMockHardware();
    const hw2 = createMockHardware();
    expect(hw1.printer).not.toBe(hw2.printer);
    expect(hw1.drawer).not.toBe(hw2.drawer);
  });

  it("printer and drawer are not the same object", () => {
    const hw = createMockHardware();
    expect(hw.printer).not.toBe(hw.drawer);
  });
});
