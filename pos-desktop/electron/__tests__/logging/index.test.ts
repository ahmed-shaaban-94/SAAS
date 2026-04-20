/**
 * Tests for the structured logger (#482 / epic #479).
 *
 * Uses an injected `destination` stream to capture emitted JSON without
 * writing to disk. Rotation itself is delegated to `pino-roll` and not
 * re-tested here — those are pino-roll's own suites.
 */

import { Writable } from "node:stream";
import {
  createLogger,
  _resetLoggerForTests,
  REDACT_PATHS_FOR_TESTS,
} from "../../logging/index";

class CaptureStream extends Writable {
  chunks: string[] = [];
  override _write(chunk: Buffer | string, _enc: BufferEncoding, cb: () => void): void {
    this.chunks.push(chunk.toString("utf8"));
    cb();
  }
  lines(): Record<string, unknown>[] {
    return this.chunks
      .join("")
      .split("\n")
      .filter(Boolean)
      .map((l) => JSON.parse(l));
  }
}

beforeEach(() => _resetLoggerForTests());

describe("logger basics", () => {
  test("emits JSON with level, timestamp, and app tag", () => {
    const dest = new CaptureStream();
    const log = createLogger({ destination: dest, level: "info" });
    log.info("boot");
    const [line] = dest.lines();
    expect(line.level).toBeDefined();
    expect(line.time).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    expect(line.app).toBe("pos-desktop");
    expect(line.msg).toBe("boot");
  });

  test("respects configured level — debug is filtered when level=info", () => {
    const dest = new CaptureStream();
    const log = createLogger({ destination: dest, level: "info" });
    log.debug("hidden");
    log.info("visible");
    const lines = dest.lines();
    expect(lines).toHaveLength(1);
    expect(lines[0].msg).toBe("visible");
  });

  test("respects LOG_LEVEL env var fallback", () => {
    const dest = new CaptureStream();
    const prev = process.env.LOG_LEVEL;
    process.env.LOG_LEVEL = "error";
    try {
      const log = createLogger({ destination: dest });
      log.warn("skip");
      log.error("keep");
      const lines = dest.lines();
      expect(lines).toHaveLength(1);
      expect(lines[0].msg).toBe("keep");
    } finally {
      if (prev === undefined) delete process.env.LOG_LEVEL;
      else process.env.LOG_LEVEL = prev;
    }
  });
});

describe("PII redaction", () => {
  test("redacts authorization header on req.headers", () => {
    const dest = new CaptureStream();
    const log = createLogger({ destination: dest });
    log.info({ req: { headers: { authorization: "Bearer leaky-token-abc" } } }, "req");
    const [line] = dest.lines();
    const req = line.req as { headers: { authorization: string } };
    expect(req.headers.authorization).toBe("[REDACTED]");
  });

  test("redacts authorization header at top level and under headers.", () => {
    const dest = new CaptureStream();
    const log = createLogger({ destination: dest });
    log.info({ headers: { authorization: "Bearer top-level" } }, "top");
    log.info({ authorization: "Bearer plain" }, "plain");
    const lines = dest.lines();
    expect((lines[0].headers as { authorization: string }).authorization).toBe("[REDACTED]");
    expect(lines[1].authorization).toBe("[REDACTED]");
  });

  test("redacts customer identifiers (national_id, customer_id, phone)", () => {
    const dest = new CaptureStream();
    const log = createLogger({ destination: dest });
    log.info(
      {
        req: { body: { national_id: "29001010101010", customer_id: "CUST-42", phone: "01012345678" } },
      },
      "purchase",
    );
    const [line] = dest.lines();
    const body = (line.req as { body: Record<string, string> }).body;
    expect(body.national_id).toBe("[REDACTED]");
    expect(body.customer_id).toBe("[REDACTED]");
    expect(body.phone).toBe("[REDACTED]");
  });

  test("redacts voucher codes wherever they appear", () => {
    const dest = new CaptureStream();
    const log = createLogger({ destination: dest });
    log.info({ voucher_code: "SUMMER2026" }, "top");
    log.info({ req: { body: { voucher_code: "SUMMER2026" } } }, "nested");
    const lines = dest.lines();
    expect(lines[0].voucher_code).toBe("[REDACTED]");
    expect((lines[1].req as { body: { voucher_code: string } }).body.voucher_code).toBe("[REDACTED]");
  });

  test("redacts nested *.password / *.token / *.refresh_token", () => {
    const dest = new CaptureStream();
    const log = createLogger({ destination: dest });
    log.info({ user: { password: "hunter2" }, session: { token: "jwt-abc" }, auth: { refresh_token: "rt-xyz" } }, "obj");
    const [line] = dest.lines();
    const user = line.user as { password: string };
    const session = line.session as { token: string };
    const auth = line.auth as { refresh_token: string };
    expect(user.password).toBe("[REDACTED]");
    expect(session.token).toBe("[REDACTED]");
    expect(auth.refresh_token).toBe("[REDACTED]");
  });

  test("redacts device_private_key under any parent key", () => {
    const dest = new CaptureStream();
    const log = createLogger({ destination: dest });
    log.info({ kp: { device_private_key: "xxx-base64-xxx" } }, "key");
    const [line] = dest.lines();
    const kp = line.kp as { device_private_key: string };
    expect(kp.device_private_key).toBe("[REDACTED]");
  });

  test("leaves non-sensitive fields untouched", () => {
    const dest = new CaptureStream();
    const log = createLogger({ destination: dest });
    log.info({ req: { body: { drug_code: "DRG-1", quantity: 2 } } }, "ok");
    const [line] = dest.lines();
    const body = (line.req as { body: { drug_code: string; quantity: number } }).body;
    expect(body.drug_code).toBe("DRG-1");
    expect(body.quantity).toBe(2);
  });

  test("does NOT leak raw authorization when logged as .err", () => {
    // Common footgun: err objects captured with headers attached. Our paths
    // cover `req.headers.authorization` + `headers.authorization`; deeper
    // nests (e.g. err.config.headers.authorization) are NOT covered unless
    // someone logs the config. This test documents the guarantee.
    const dest = new CaptureStream();
    const log = createLogger({ destination: dest });
    log.error({ req: { headers: { authorization: "Bearer must-hide" } } }, "err");
    expect(JSON.stringify(dest.lines()[0])).not.toContain("must-hide");
  });
});

describe("release + environment base bindings", () => {
  test("stamps `release` on every log line when supplied", () => {
    const dest = new CaptureStream();
    const log = createLogger({ destination: dest, release: "1.2.3" });
    log.info("boot");
    log.info({ step: "ready" }, "second");
    const lines = dest.lines();
    expect(lines).toHaveLength(2);
    for (const line of lines) {
      expect(line.release).toBe("1.2.3");
    }
  });

  test("stamps `environment` on every log line when supplied", () => {
    const dest = new CaptureStream();
    const log = createLogger({ destination: dest, environment: "production" });
    log.info("one");
    log.error("two");
    const lines = dest.lines();
    expect(lines).toHaveLength(2);
    for (const line of lines) {
      expect(line.environment).toBe("production");
    }
  });

  test("omits `release` and `environment` when neither is supplied", () => {
    const dest = new CaptureStream();
    const log = createLogger({ destination: dest });
    log.info("boot");
    const [line] = dest.lines();
    expect(line).not.toHaveProperty("release");
    expect(line).not.toHaveProperty("environment");
    // `app` always present — guards against accidentally breaking the base map.
    expect(line.app).toBe("pos-desktop");
  });

  test("both fields coexist alongside ad-hoc bindings at log time", () => {
    const dest = new CaptureStream();
    const log = createLogger({
      destination: dest,
      release: "1.0.0-alpha",
      environment: "staging",
    });
    log.info({ module: "boot", version: 1 }, "ready");
    const [line] = dest.lines();
    expect(line.release).toBe("1.0.0-alpha");
    expect(line.environment).toBe("staging");
    expect(line.module).toBe("boot");
    expect(line.version).toBe(1);
    expect(line.app).toBe("pos-desktop");
  });
});

describe("singleton + reinit semantics", () => {
  test("second call without reinit returns the cached instance", () => {
    const first = createLogger({ level: "info" });
    const second = createLogger({ level: "error" });
    expect(second).toBe(first);
    // Level override from the second call was ignored (proves caching).
    expect(first.level).toBe("info");
  });

  test("reinit: true discards the cache and applies fresh deps", () => {
    const first = createLogger({ level: "info" });
    const reinited = createLogger({ level: "error", reinit: true });
    expect(reinited).not.toBe(first);
    expect(reinited.level).toBe("error");
  });

  test("reinit replaces the cached instance seen by subsequent callers", () => {
    const first = createLogger({ level: "info" });
    const reinited = createLogger({ level: "warn", reinit: true });
    // A third call without reinit now hands back the reinited instance,
    // not the original.
    const third = createLogger();
    expect(third).toBe(reinited);
    expect(third).not.toBe(first);
    expect(third.level).toBe("warn");
  });

  test("destination-injected loggers still bypass the cache entirely", () => {
    // This is the pre-existing tests-only path — reinit should not change it.
    createLogger({ level: "info" });
    const dest = new CaptureStream();
    const destLogger = createLogger({ destination: dest, level: "debug" });
    destLogger.debug("x");
    expect(dest.lines()).toHaveLength(1);
    // And the singleton (created by the first call) is untouched by the
    // destination-injected call.
    const cached = createLogger();
    expect(cached).not.toBe(destLogger);
  });
});

describe("redact paths export", () => {
  test("export is frozen-ish: includes the must-have fields", () => {
    // If someone removes a field, this test yells. Paired with the assertion
    // in the "no PII in logs" manual check before shipping installers.
    const must = [
      "req.headers.authorization",
      "req.body.national_id",
      "req.body.customer_id",
      "req.body.phone",
      "voucher_code",
      "*.password",
      "*.token",
      "*.device_private_key",
    ];
    for (const path of must) {
      expect(REDACT_PATHS_FOR_TESTS).toContain(path);
    }
  });
});
