import {
  FINGERPRINT_V2_PREFIX,
  computeFingerprintV2,
  pickPrimaryMac,
  readMachineId,
  type ComputeFingerprintDeps,
  type NodeInetInterface,
} from "../../authz/fingerprint";

// ─── pickPrimaryMac ─────────────────────────────────────────────────────────

describe("pickPrimaryMac", () => {
  function iface(mac: string, opts: Partial<NodeInetInterface> = {}): NodeInetInterface {
    return {
      address: "192.168.1.2",
      mac,
      internal: false,
      family: "IPv4",
      ...opts,
    };
  }

  it("returns empty string when no interfaces", () => {
    expect(pickPrimaryMac({})).toBe("");
  });

  it("skips loopback interfaces", () => {
    const ifaces = {
      lo: [iface("00:00:00:00:00:00", { internal: true })],
    };
    expect(pickPrimaryMac(ifaces)).toBe("");
  });

  it("skips docker bridge interfaces", () => {
    const ifaces = {
      docker0: [iface("02:42:ac:11:00:01")],
      "br-abc123": [iface("02:42:ac:12:00:01")],
    };
    expect(pickPrimaryMac(ifaces)).toBe("");
  });

  it("skips veth / vmnet / virbr / vEthernet / VMware / VirtualBox virtuals", () => {
    const ifaces = {
      veth1: [iface("aa:bb:cc:dd:ee:01")],
      vmnet1: [iface("aa:bb:cc:dd:ee:02")],
      virbr0: [iface("aa:bb:cc:dd:ee:03")],
      "vEthernet (Default Switch)": [iface("aa:bb:cc:dd:ee:04")],
      VMware1: [iface("aa:bb:cc:dd:ee:05")],
      VirtualBox0: [iface("aa:bb:cc:dd:ee:06")],
      Bluetooth: [iface("aa:bb:cc:dd:ee:07")],
      tun0: [iface("aa:bb:cc:dd:ee:08")],
      tap0: [iface("aa:bb:cc:dd:ee:09")],
    };
    expect(pickPrimaryMac(ifaces)).toBe("");
  });

  it("returns first non-virtual interface's MAC", () => {
    const ifaces = {
      eth0: [iface("AA:BB:CC:11:22:33")],
    };
    expect(pickPrimaryMac(ifaces)).toBe("aa:bb:cc:11:22:33");
  });

  it("lowercases the MAC regardless of input casing", () => {
    const ifaces = { eth0: [iface("AA:BB:CC:DD:EE:FF")] };
    expect(pickPrimaryMac(ifaces)).toBe("aa:bb:cc:dd:ee:ff");
  });

  it("is deterministic across arbitrary key ordering", () => {
    const a = { wlan0: [iface("11:22:33:44:55:66")], eth0: [iface("aa:bb:cc:dd:ee:ff")] };
    const b = { eth0: [iface("aa:bb:cc:dd:ee:ff")], wlan0: [iface("11:22:33:44:55:66")] };
    // Both should pick eth0 (sorts alphabetically before wlan0)
    expect(pickPrimaryMac(a)).toBe(pickPrimaryMac(b));
    expect(pickPrimaryMac(a)).toBe("aa:bb:cc:dd:ee:ff");
  });

  it("skips internal flag even on non-virtual names", () => {
    const ifaces = {
      eth0: [iface("aa:bb:cc:dd:ee:01", { internal: true })],
      eth1: [iface("aa:bb:cc:dd:ee:02")],
    };
    expect(pickPrimaryMac(ifaces)).toBe("aa:bb:cc:dd:ee:02");
  });

  it("skips null-MAC entries", () => {
    const ifaces = {
      eth0: [iface("00:00:00:00:00:00")],
      eth1: [iface("aa:bb:cc:dd:ee:02")],
    };
    expect(pickPrimaryMac(ifaces)).toBe("aa:bb:cc:dd:ee:02");
  });

  it("prefers first non-empty entry within an interface's info list", () => {
    const ifaces = {
      eth0: [
        iface("", { family: "IPv6" }),
        iface("aa:bb:cc:dd:ee:01", { family: "IPv4" }),
      ],
    };
    expect(pickPrimaryMac(ifaces)).toBe("aa:bb:cc:dd:ee:01");
  });
});

// ─── readMachineId ──────────────────────────────────────────────────────────

describe("readMachineId", () => {
  it("reads Windows MachineGuid from reg query output", () => {
    const deps: ComputeFingerprintDeps = {
      platform: () => "win32",
      execSync: () =>
        "\r\nHKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Cryptography\r\n" +
        "    MachineGuid    REG_SZ    ABCDEF01-2345-6789-ABCD-EF0123456789\r\n\r\n",
    };
    expect(readMachineId(deps)).toBe("abcdef01-2345-6789-abcd-ef0123456789");
  });

  it("returns empty string when Windows reg query throws", () => {
    const deps: ComputeFingerprintDeps = {
      platform: () => "win32",
      execSync: () => {
        throw new Error("registry key not found");
      },
    };
    expect(readMachineId(deps)).toBe("");
  });

  it("returns empty string when reg output doesn't match pattern", () => {
    const deps: ComputeFingerprintDeps = {
      platform: () => "win32",
      execSync: () => "garbage output",
    };
    expect(readMachineId(deps)).toBe("");
  });

  it("reads macOS IOPlatformUUID from ioreg output", () => {
    const deps: ComputeFingerprintDeps = {
      platform: () => "darwin",
      execSync: () =>
        '| |   {\n' +
        '    "IOPlatformUUID" = "AAAA1111-BBBB-2222-CCCC-333344445555"\n' +
        '    "other-field" = "ignored"\n',
    };
    expect(readMachineId(deps)).toBe("aaaa1111-bbbb-2222-cccc-333344445555");
  });

  it("returns empty string when macOS ioreg throws", () => {
    const deps: ComputeFingerprintDeps = {
      platform: () => "darwin",
      execSync: () => {
        throw new Error("ioreg not found");
      },
    };
    expect(readMachineId(deps)).toBe("");
  });

  it("reads Linux /etc/machine-id", () => {
    const deps: ComputeFingerprintDeps = {
      platform: () => "linux",
      readFile: (p) => {
        if (p === "/etc/machine-id") return "AABBCCDDEEFF00112233445566778899\n";
        throw new Error("not found");
      },
    };
    expect(readMachineId(deps)).toBe("aabbccddeeff00112233445566778899");
  });

  it("falls back to /var/lib/dbus/machine-id when /etc is unreadable", () => {
    const deps: ComputeFingerprintDeps = {
      platform: () => "linux",
      readFile: (p) => {
        if (p === "/etc/machine-id") throw new Error("ENOENT");
        if (p === "/var/lib/dbus/machine-id") return "ffeeddccbbaa99887766554433221100\n";
        throw new Error("not found");
      },
    };
    expect(readMachineId(deps)).toBe("ffeeddccbbaa99887766554433221100");
  });

  it("returns empty string when neither linux path is readable", () => {
    const deps: ComputeFingerprintDeps = {
      platform: () => "linux",
      readFile: () => {
        throw new Error("ENOENT");
      },
    };
    expect(readMachineId(deps)).toBe("");
  });
});

// ─── computeFingerprintV2 ───────────────────────────────────────────────────

describe("computeFingerprintV2", () => {
  function makeDeps(overrides: Partial<ComputeFingerprintDeps> = {}): ComputeFingerprintDeps {
    return {
      hostname: () => "host-1",
      platform: () => "linux",
      networkInterfaces: () => ({
        eth0: [{ address: "1.2.3.4", mac: "aa:bb:cc:dd:ee:01", internal: false, family: "IPv4" }],
      }),
      readFile: () => "machine-id-value-0000000000000000\n",
      execSync: () => "",
      ...overrides,
    };
  }

  it("returns digest with sha256v2: prefix and 64 hex chars", () => {
    const r = computeFingerprintV2(makeDeps());
    expect(r.digest).toMatch(/^sha256v2:[0-9a-f]{64}$/);
    expect(r.digest.startsWith(FINGERPRINT_V2_PREFIX)).toBe(true);
  });

  it("is stable for identical inputs", () => {
    const d = makeDeps();
    expect(computeFingerprintV2(d).digest).toBe(computeFingerprintV2(d).digest);
  });

  it("differs when hostname differs", () => {
    const a = computeFingerprintV2(makeDeps({ hostname: () => "host-a" }));
    const b = computeFingerprintV2(makeDeps({ hostname: () => "host-b" }));
    expect(a.digest).not.toBe(b.digest);
  });

  it("differs when primary MAC differs", () => {
    const a = computeFingerprintV2(makeDeps());
    const b = computeFingerprintV2(
      makeDeps({
        networkInterfaces: () => ({
          eth0: [{ address: "1.2.3.4", mac: "ff:ee:dd:cc:bb:aa", internal: false, family: "IPv4" }],
        }),
      }),
    );
    expect(a.digest).not.toBe(b.digest);
  });

  it("differs when machineId differs", () => {
    const a = computeFingerprintV2(
      makeDeps({ readFile: () => "machine-id-value-aaaaaaaaaaaaaaaa\n" }),
    );
    const b = computeFingerprintV2(
      makeDeps({ readFile: () => "machine-id-value-bbbbbbbbbbbbbbbb\n" }),
    );
    expect(a.digest).not.toBe(b.digest);
  });

  it("reliable=true when both machineId and MAC are present", () => {
    const r = computeFingerprintV2(makeDeps());
    expect(r.reliable).toBe(true);
    expect(r.components.machineId).toBe("machine-id-value-0000000000000000");
    expect(r.components.primaryMac).toBe("aa:bb:cc:dd:ee:01");
  });

  it("reliable=true when only machineId is present (no MAC)", () => {
    const r = computeFingerprintV2(
      makeDeps({
        networkInterfaces: () => ({}),
      }),
    );
    expect(r.reliable).toBe(true);
    expect(r.components.primaryMac).toBe("");
  });

  it("reliable=true when only MAC is present (no machineId)", () => {
    const r = computeFingerprintV2(
      makeDeps({
        readFile: () => {
          throw new Error("ENOENT");
        },
        execSync: () => {
          throw new Error("no ioreg/reg");
        },
      }),
    );
    expect(r.reliable).toBe(true);
    expect(r.components.machineId).toBe("");
    expect(r.components.primaryMac).toBe("aa:bb:cc:dd:ee:01");
  });

  it("reliable=false when both are unavailable (bare CI sandbox)", () => {
    const r = computeFingerprintV2(
      makeDeps({
        networkInterfaces: () => ({}),
        readFile: () => {
          throw new Error("ENOENT");
        },
        execSync: () => {
          throw new Error("no ioreg/reg");
        },
      }),
    );
    expect(r.reliable).toBe(false);
    // Still produces a digest — it's just hostname-only, flagged as unreliable.
    expect(r.digest).toMatch(/^sha256v2:[0-9a-f]{64}$/);
  });

  it("exposes components with hostname/machineId/primaryMac", () => {
    const r = computeFingerprintV2(makeDeps({ hostname: () => "my-host" }));
    expect(r.components.hostname).toBe("my-host");
    expect(r.components.machineId).toBe("machine-id-value-0000000000000000");
    expect(r.components.primaryMac).toBe("aa:bb:cc:dd:ee:01");
  });

  it("uses Windows MachineGuid on win32 platform", () => {
    const r = computeFingerprintV2(
      makeDeps({
        platform: () => "win32",
        execSync: () =>
          "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Cryptography\r\n" +
          "    MachineGuid    REG_SZ    12345678-abcd-ef01-2345-6789abcdef01\r\n",
      }),
    );
    expect(r.reliable).toBe(true);
    expect(r.components.machineId).toBe("12345678-abcd-ef01-2345-6789abcdef01");
  });

  it("uses macOS IOPlatformUUID on darwin platform", () => {
    const r = computeFingerprintV2(
      makeDeps({
        platform: () => "darwin",
        execSync: () => '"IOPlatformUUID" = "FEEDFACE-DEAD-BEEF-CAFE-BABE12345678"',
      }),
    );
    expect(r.reliable).toBe(true);
    expect(r.components.machineId).toBe("feedface-dead-beef-cafe-babe12345678");
  });
});
