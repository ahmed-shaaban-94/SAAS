/**
 * Tests for the hardware factory (hardware/index.ts).
 *
 * Real-mode uses node-thermal-printer which may not be available in CI.
 * We mock the RealPrinter, RealDrawer, and createScanner modules so the
 * factory can be exercised without native bindings.
 */

jest.mock("../../hardware/printer", () => ({
  RealPrinter: jest.fn().mockImplementation(() => ({
    print: jest.fn(),
    status: jest.fn(),
    testPrint: jest.fn(),
  })),
}));

jest.mock("../../hardware/drawer", () => ({
  RealDrawer: jest.fn().mockImplementation(() => ({
    open: jest.fn(),
  })),
}));

jest.mock("../../hardware/scanner", () => ({
  createScanner: jest.fn().mockReturnValue({ on: jest.fn() }),
}));

import { createHardware } from "../../hardware/index";
import { MockPrinter, MockDrawer, takePrinterLog, takeDrawerLog } from "../../hardware/mock";
import { RealPrinter } from "../../hardware/printer";
import { RealDrawer } from "../../hardware/drawer";
import { createScanner } from "../../hardware/scanner";

const MockedRealPrinter = RealPrinter as jest.MockedClass<typeof RealPrinter>;
const MockedRealDrawer = RealDrawer as jest.MockedClass<typeof RealDrawer>;
const mockedCreateScanner = createScanner as jest.MockedFunction<typeof createScanner>;

beforeEach(() => {
  // Drain stale log entries from module-level shared arrays
  takePrinterLog();
  takeDrawerLog();
  jest.clearAllMocks();
});

describe("createHardware", () => {
  describe("mock mode", () => {
    it("returns mode='mock' when called with no arguments", () => {
      const hw = createHardware();
      expect(hw.mode).toBe("mock");
    });

    it("returns mode='mock' when called with 'mock'", () => {
      const hw = createHardware("mock");
      expect(hw.mode).toBe("mock");
    });

    it("has a printer in mock mode", () => {
      const hw = createHardware("mock");
      expect(hw.printer).toBeInstanceOf(MockPrinter);
    });

    it("has a drawer in mock mode", () => {
      const hw = createHardware("mock");
      expect(hw.drawer).toBeInstanceOf(MockDrawer);
    });

    it("has a scanner in mock mode", () => {
      const hw = createHardware("mock");
      expect(hw.scanner).toBeDefined();
    });

    it("does NOT instantiate RealPrinter or RealDrawer in mock mode", () => {
      createHardware("mock");
      expect(MockedRealPrinter).not.toHaveBeenCalled();
      expect(MockedRealDrawer).not.toHaveBeenCalled();
    });

    it("calls createScanner() once per factory call", () => {
      createHardware("mock");
      expect(mockedCreateScanner).toHaveBeenCalledTimes(1);
    });
  });

  describe("real mode", () => {
    it("does NOT throw when printerInterface is provided", () => {
      expect(() =>
        createHardware("real", { printerInterface: "tcp://192.168.1.100:9100" }),
      ).not.toThrow();
    });

    it("returns mode='real'", () => {
      const hw = createHardware("real", { printerInterface: "tcp://192.168.1.100:9100" });
      expect(hw.mode).toBe("real");
    });

    it("has a printer in real mode", () => {
      const hw = createHardware("real", { printerInterface: "tcp://192.168.1.100:9100" });
      expect(hw.printer).toBeDefined();
    });

    it("has a drawer in real mode", () => {
      const hw = createHardware("real", { printerInterface: "tcp://192.168.1.100:9100" });
      expect(hw.drawer).toBeDefined();
    });

    it("has a scanner in real mode", () => {
      const hw = createHardware("real", { printerInterface: "tcp://192.168.1.100:9100" });
      expect(hw.scanner).toBeDefined();
    });

    it("instantiates RealPrinter with the given interface", () => {
      createHardware("real", { printerInterface: "tcp://192.168.1.100:9100" });
      expect(MockedRealPrinter).toHaveBeenCalledWith(
        "tcp://192.168.1.100:9100",
        undefined,
      );
    });

    it("passes printerType to RealPrinter when provided", () => {
      createHardware("real", { printerInterface: "//./COM3", printerType: "STAR" });
      expect(MockedRealPrinter).toHaveBeenCalledWith("//./COM3", "STAR");
    });

    it("instantiates RealDrawer", () => {
      createHardware("real", { printerInterface: "tcp://192.168.1.100:9100" });
      expect(MockedRealDrawer).toHaveBeenCalled();
    });

    it("throws when called without config", () => {
      expect(() => createHardware("real")).toThrow();
    });

    it("throws when printerInterface is missing from config", () => {
      expect(() =>
        createHardware("real", {} as { printerInterface: string }),
      ).toThrow();
    });

    it("error message contains 'printer_interface'", () => {
      expect(() => createHardware("real")).toThrow(/printer_interface/);
    });
  });
});
