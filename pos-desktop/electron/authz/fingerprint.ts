/**
 * Machine fingerprint v2 — OS-level identifiers (#480 / epic #479).
 *
 * The v1 fingerprint in `./keys.ts::computeDeviceFingerprintV1` was
 * install-specific: `sha256(hostname + deviceUuid)` where `deviceUuid` is
 * a random UUID persisted on first run. A full OS reinstall wiped the
 * SQLite file → new UUID → the same physical machine looked like a new
 * device. That defeats "one physical machine per terminal."
 *
 * v2 augments the digest with identifiers that survive a Windows reinstall
 * on the same hardware:
 *
 *   Windows:  MachineGuid from `HKLM\SOFTWARE\Microsoft\Cryptography`
 *             (rebuilt by Windows setup but stable across reimages of the
 *              same disk; the registry key is preserved during in-place
 *              repair installs. Clean installs regenerate it — we accept
 *              this as the edge case that requires admin re-registration.)
 *   macOS:    IOPlatformUUID via `ioreg -rd1 -c IOPlatformExpertDevice`
 *   Linux:    `/etc/machine-id` (systemd-generated, survives reinstall
 *              only if `/etc` is preserved; for production POS we expect
 *              Windows so this is mostly test-scaffolding)
 *
 * Secondary factor: first non-loopback, non-virtual MAC address. A NIC
 * swap changes the MAC, so this catches hardware-level tampering even if
 * the machine-id is forged. (Virtual interfaces like Docker / VMware are
 * filtered out — they're not a stable part of the machine identity.)
 *
 * Tertiary factor: hostname. Cheap sanity check against misconfiguration.
 *
 * Digest: `sha256("v2|<hostname>|<machineId>|<firstMac>")` → `sha256v2:<hex>`.
 * The prefix is deliberately different from v1's `sha256:` so callers can
 * never confuse the two strings.
 *
 * Graceful degradation: if `machineId` can't be read (missing registry
 * access, no systemd on Linux, no ioreg on macOS, tests under CI) we still
 * produce a fingerprint but flag the `reliable=false` bit so the caller
 * can decide whether to trust it. The register-device flow uses the
 * reliable flag to refuse to register on un-fingerprintable hosts.
 *
 * Design ref: issue #480, epic #479.
 */

import { createHash } from "node:crypto";
import { execSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { hostname, networkInterfaces, platform } from "node:os";

export const FINGERPRINT_V2_PREFIX = "sha256v2:" as const;

export interface FingerprintComponents {
  /** Platform-level stable id. Empty string if unreadable. */
  machineId: string;
  /** First non-loopback non-virtual MAC (colon-separated lowercase). Empty if none. */
  primaryMac: string;
  /** os.hostname() — used as a tiebreaker. */
  hostname: string;
}

export interface FingerprintResult {
  /** `sha256v2:<hex>` digest. Safe to persist + send to the server. */
  digest: string;
  /** Individual components (kept for diagnostics only — never logged verbatim). */
  components: FingerprintComponents;
  /**
   * `true` iff at least one of `machineId` OR `primaryMac` was readable.
   * False on stripped-down CI sandboxes with neither — callers should
   * refuse to register devices in that state.
   */
  reliable: boolean;
}

export interface ComputeFingerprintDeps {
  /** Override `os.hostname()` (tests). */
  hostname?: () => string;
  /** Override `os.platform()` (tests). */
  platform?: () => NodeJS.Platform;
  /** Override network interface enumeration (tests). */
  networkInterfaces?: () => NodeJS.Dict<NodeInetInterface[]>;
  /** Override `execSync` for Windows reg / macOS ioreg (tests). */
  execSync?: (cmd: string, opts?: { encoding: "utf8"; stdio?: "pipe" | "ignore" }) => string;
  /** Override fs.readFileSync for `/etc/machine-id` (tests). */
  readFile?: (p: string, enc: "utf8") => string;
}

// Minimal NetworkInterfaceInfo subset we need. Declared locally so tests
// don't have to import Node's types.
export interface NodeInetInterface {
  address: string;
  mac: string;
  internal: boolean;
  family: string;
}

const VIRTUAL_IFACE_PATTERNS: readonly RegExp[] = [
  /^(lo|loopback)/i,
  /^docker/i,
  /^br-/i,
  /^veth/i,
  /^vmnet/i,
  /^virbr/i,
  /^vEthernet/i,
  /^VMware/i,
  /^VirtualBox/i,
  /^Bluetooth/i,
  /^tun\d*$/i,
  /^tap\d*$/i,
];

function isVirtualIfaceName(name: string): boolean {
  return VIRTUAL_IFACE_PATTERNS.some((re) => re.test(name));
}

const NULL_MAC = "00:00:00:00:00:00";

/**
 * Pick a stable MAC from all non-loopback, non-virtual interfaces. Returns
 * an empty string if nothing usable is found.
 *
 * Ordering: interfaces are sorted by name before scanning so the chosen
 * MAC is deterministic across boots even if the OS reorders them.
 */
export function pickPrimaryMac(
  ifaces: NodeJS.Dict<NodeInetInterface[]>,
): string {
  const names = Object.keys(ifaces).sort();
  for (const name of names) {
    if (isVirtualIfaceName(name)) continue;
    const list = ifaces[name] ?? [];
    for (const info of list) {
      if (info.internal) continue;
      const mac = (info.mac ?? "").toLowerCase();
      if (!mac || mac === NULL_MAC) continue;
      return mac;
    }
  }
  return "";
}

type ExecRunner = NonNullable<ComputeFingerprintDeps["execSync"]>;

const defaultExec: ExecRunner = (cmd, opts) =>
  execSync(cmd, opts) as unknown as string;

function readWindowsMachineGuid(exec: ComputeFingerprintDeps["execSync"]): string {
  const runner: ExecRunner = exec ?? defaultExec;
  try {
    // `reg query` prints a block like:
    //   HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Cryptography
    //       MachineGuid    REG_SZ    <guid>
    const out = runner(
      'reg query "HKLM\\SOFTWARE\\Microsoft\\Cryptography" /v MachineGuid',
      { encoding: "utf8", stdio: "pipe" },
    );
    const match = out.match(/MachineGuid\s+REG_SZ\s+([0-9a-fA-F-]+)/);
    return match ? match[1].toLowerCase() : "";
  } catch {
    return "";
  }
}

function readMacOsPlatformUuid(exec: ComputeFingerprintDeps["execSync"]): string {
  const runner: ExecRunner = exec ?? defaultExec;
  try {
    const out = runner(
      'ioreg -rd1 -c IOPlatformExpertDevice',
      { encoding: "utf8", stdio: "pipe" },
    );
    const match = out.match(/"IOPlatformUUID"\s*=\s*"([^"]+)"/);
    return match ? match[1].toLowerCase() : "";
  } catch {
    return "";
  }
}

function readLinuxMachineId(read: ComputeFingerprintDeps["readFile"]): string {
  const reader = read ?? ((p: string, enc: "utf8") => readFileSync(p, enc));
  // `/etc/machine-id` is preferred; `/var/lib/dbus/machine-id` is the
  // fallback on older distros. Both are 32 lowercase hex chars.
  const paths = ["/etc/machine-id", "/var/lib/dbus/machine-id"];
  for (const p of paths) {
    try {
      return reader(p, "utf8").trim().toLowerCase();
    } catch {
      /* try next path */
    }
  }
  return "";
}

export function readMachineId(deps: ComputeFingerprintDeps = {}): string {
  const plat = (deps.platform ?? platform)();
  switch (plat) {
    case "win32":
      return readWindowsMachineGuid(deps.execSync);
    case "darwin":
      return readMacOsPlatformUuid(deps.execSync);
    default:
      return readLinuxMachineId(deps.readFile);
  }
}

/**
 * Compute the v2 fingerprint. Pure — no side effects, no DB access. The
 * caller is responsible for persisting the digest and comparing against a
 * stored value on subsequent boots.
 */
export function computeFingerprintV2(
  deps: ComputeFingerprintDeps = {},
): FingerprintResult {
  const host = (deps.hostname ?? hostname)();
  const ifaces = (deps.networkInterfaces ?? networkInterfaces)() as NodeJS.Dict<
    NodeInetInterface[]
  >;
  const primaryMac = pickPrimaryMac(ifaces);
  const machineId = readMachineId(deps);

  const reliable = machineId !== "" || primaryMac !== "";

  // Keep the canonical order: version tag, hostname, machineId, primaryMac.
  // Adding new fields later MUST bump the prefix (v3…) so old digests
  // don't silently match newly-formatted strings.
  const canonical = ["v2", host, machineId, primaryMac].join("|");
  const digest =
    FINGERPRINT_V2_PREFIX + createHash("sha256").update(canonical, "utf8").digest("hex");

  return {
    digest,
    components: { machineId, primaryMac, hostname: host },
    reliable,
  };
}
