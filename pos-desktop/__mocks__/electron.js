// Jest manual mock for the 'electron' module.
// In unit tests, Electron's native APIs are unavailable. This mock provides
// minimal stubs so tests that import electron-dependent modules can run.

const safeStorage = {
  isEncryptionAvailable: jest.fn(() => false),
  encryptString: jest.fn((plaintext) => Buffer.from(plaintext, "utf8")),
  decryptString: jest.fn((buf) => buf.toString("utf8")),
};

const app = {
  getPath: jest.fn(() => "/tmp/datapulse-test"),
  getVersion: jest.fn(() => "0.0.0-test"),
};

module.exports = { safeStorage, app };
