import Database from "better-sqlite3";
import * as path from "path";
import { applySchema } from "../../db/migrate";
import { isDeviceRegistered, registerDevice } from "../../authz/device";

// ─── Module mocks ───────────────────────────────────────────────────────────

jest.mock("../../authz/keys", () => ({
  getOrCreateKeypair: jest.fn().mockReturnValue({ publicKey: "pub_b64url", privateKey: "priv_b64url" }),
  computeDeviceFingerprint: jest.fn().mockReturnValue("sha256:aabbccdd"),
}));

jest.mock("../../db/settings", () => ({
  getSetting: jest.fn(),
  setSetting: jest.fn(),
}));

// ─── Helpers ─────────────────────────────────────────────────────────────────

const { getSetting, setSetting } = jest.requireMock("../../db/settings") as {
  getSetting: jest.Mock;
  setSetting: jest.Mock;
};

const { getOrCreateKeypair, computeDeviceFingerprint } = jest.requireMock("../../authz/keys") as {
  getOrCreateKeypair: jest.Mock;
  computeDeviceFingerprint: jest.Mock;
};

const SCHEMA_PATH = path.join(__dirname, "../../db/schema.sql");

function openTestDb(): Database.Database {
  const db = new Database(":memory:");
  applySchema(db, SCHEMA_PATH);
  return db;
}

// ─── Tests ───────────────────────────────────────────────────────────────────

beforeEach(() => {
  jest.clearAllMocks();
  // Reset fetch mock
  (global as Record<string, unknown>).fetch = jest.fn();
});

describe("isDeviceRegistered", () => {
  let db: Database.Database;

  beforeEach(() => {
    db = openTestDb();
  });
  afterEach(() => {
    db.close();
  });

  it("returns true when getSetting returns 'true'", () => {
    getSetting.mockReturnValue("true");
    expect(isDeviceRegistered(db)).toBe(true);
    expect(getSetting).toHaveBeenCalledWith(db, "device_registered");
  });

  it("returns false when getSetting returns null", () => {
    getSetting.mockReturnValue(null);
    expect(isDeviceRegistered(db)).toBe(false);
  });

  it("returns false when getSetting returns any other string", () => {
    getSetting.mockReturnValue("false");
    expect(isDeviceRegistered(db)).toBe(false);
  });
});

describe("registerDevice", () => {
  let db: Database.Database;

  const opts = {
    baseUrl: "https://api.example.com",
    jwt: "test.jwt.token",
    terminalId: 42,
  };

  beforeEach(() => {
    db = openTestDb();
  });
  afterEach(() => {
    db.close();
  });

  it("calls fetch with correct URL, method, headers and body", async () => {
    const fakeResult = { device_id: 7, terminal_id: 42 };
    (global as Record<string, unknown>).fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => fakeResult,
    });

    await registerDevice(db, opts);

    expect(fetch).toHaveBeenCalledWith(
      "https://api.example.com/api/v1/pos/terminals/register-device",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          "Content-Type": "application/json",
          Authorization: "Bearer test.jwt.token",
        }),
        body: expect.any(String),
      }),
    );

    const callArgs = (fetch as jest.Mock).mock.calls[0];
    const body = JSON.parse(callArgs[1].body as string);
    expect(body.terminal_id).toBe(42);
    expect(body.public_key).toBe("pub_b64url");
    expect(body.device_fingerprint).toBe("sha256:aabbccdd");
  });

  it("uses getOrCreateKeypair and computeDeviceFingerprint", async () => {
    (global as Record<string, unknown>).fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ device_id: 1, terminal_id: 42 }),
    });

    await registerDevice(db, opts);

    expect(getOrCreateKeypair).toHaveBeenCalledWith(db);
    expect(computeDeviceFingerprint).toHaveBeenCalledWith(db);
  });

  it("calls setSetting('device_registered','true') and setSetting('device_id', ...) on success", async () => {
    const fakeResult = { device_id: 99, terminal_id: 42 };
    (global as Record<string, unknown>).fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => fakeResult,
    });

    await registerDevice(db, opts);

    expect(setSetting).toHaveBeenCalledWith(db, "device_registered", "true");
    expect(setSetting).toHaveBeenCalledWith(db, "device_id", "99");
  });

  it("returns device_id and terminal_id from server response", async () => {
    const fakeResult = { device_id: 5, terminal_id: 42 };
    (global as Record<string, unknown>).fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => fakeResult,
    });

    const result = await registerDevice(db, opts);

    expect(result).toEqual({ device_id: 5, terminal_id: 42 });
  });

  it("throws with HTTP status in message when response is not ok", async () => {
    (global as Record<string, unknown>).fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 403,
      text: async () => "forbidden",
    });

    await expect(registerDevice(db, opts)).rejects.toThrow("HTTP 403");
  });

  it("does not call setSetting when response is not ok", async () => {
    (global as Record<string, unknown>).fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 500,
      text: async () => "internal server error",
    });

    await expect(registerDevice(db, opts)).rejects.toThrow();
    expect(setSetting).not.toHaveBeenCalledWith(db, "device_registered", "true");
  });

  it("truncates response body to 200 chars in error message", async () => {
    const longBody = "x".repeat(300);
    (global as Record<string, unknown>).fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 422,
      text: async () => longBody,
    });

    await expect(registerDevice(db, opts)).rejects.toThrow(
      expect.objectContaining({
        message: expect.stringMatching(/x{200}$/),
      }),
    );
  });
});
