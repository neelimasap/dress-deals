const assert = require("node:assert/strict");
const test = require("node:test");

const { authorizeRefresh, queueRefresh } = require("../api/refresh-core.cjs");

test("refresh authorization rejects a missing token", () => {
  const result = authorizeRefresh({ headers: {} }, "expected-secret");
  assert.deepEqual(result, { ok: false, status: 401, error: "Unauthorized" });
});

test("refresh authorization accepts the configured bearer token", () => {
  const result = authorizeRefresh(
    { headers: { authorization: "Bearer expected-secret" } },
    "expected-secret"
  );
  assert.deepEqual(result, { ok: true });
});

test("bad GitHub responses are converted to a safe 502", async () => {
  const result = await queueRefresh({
    env: { GITHUB_TOKEN: "token", GITHUB_REPOSITORY: "owner/repo" },
    fetchImpl: async () => ({ ok: false, status: 403, text: async () => "sensitive upstream detail" })
  });

  assert.equal(result.status, 502);
  assert.equal(result.payload.error, "GitHub workflow dispatch failed");
  assert.equal("details" in result.payload, false);
});

test("successful GitHub dispatch returns accepted", async () => {
  const result = await queueRefresh({
    env: { GITHUB_TOKEN: "token", GITHUB_REPOSITORY: "owner/repo" },
    fetchImpl: async () => ({ ok: true, status: 204, text: async () => "" })
  });

  assert.equal(result.status, 202);
  assert.equal(result.payload.ok, true);
});
