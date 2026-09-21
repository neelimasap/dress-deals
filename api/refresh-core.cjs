const { timingSafeEqual } = require("node:crypto");

function readHeader(request, name) {
  if (request?.headers?.get) {
    return request.headers.get(name) || "";
  }
  const expected = name.toLowerCase();
  const entry = Object.entries(request?.headers || {}).find(([key]) => key.toLowerCase() === expected);
  return entry ? String(entry[1]) : "";
}

function safeEqual(left, right) {
  const leftBuffer = Buffer.from(String(left));
  const rightBuffer = Buffer.from(String(right));
  return leftBuffer.length === rightBuffer.length && timingSafeEqual(leftBuffer, rightBuffer);
}

function authorizeRefresh(request, expectedSecret) {
  if (!expectedSecret) {
    return { ok: false, status: 503, error: "Refresh authentication is not configured" };
  }

  const authorization = readHeader(request, "authorization");
  const suppliedSecret = authorization.startsWith("Bearer ")
    ? authorization.slice("Bearer ".length).trim()
    : readHeader(request, "x-refresh-token").trim();

  if (!suppliedSecret || !safeEqual(suppliedSecret, expectedSecret)) {
    return { ok: false, status: 401, error: "Unauthorized" };
  }
  return { ok: true };
}

async function queueRefresh({ env = process.env, fetchImpl = fetch, source = "vercel-refresh" } = {}) {
  const token = env.GITHUB_TOKEN;
  const repository = env.GITHUB_REPOSITORY || "neelimasap/dress-deals";
  const workflowId = env.GITHUB_REFRESH_WORKFLOW || "daily-refresh.yml";
  const ref = env.GITHUB_REFRESH_REF || "main";

  if (!token) {
    return { status: 503, payload: { ok: false, error: "Refresh service is not configured" } };
  }

  const [owner, repo, ...extra] = repository.split("/");
  if (!owner || !repo || extra.length) {
    return { status: 500, payload: { ok: false, error: "Invalid GITHUB_REPOSITORY" } };
  }

  try {
    const githubResponse = await fetchImpl(
      `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflowId}/dispatches`,
      {
        method: "POST",
        headers: {
          Accept: "application/vnd.github+json",
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          "User-Agent": "dress-deals-refresh"
        },
        body: JSON.stringify({ ref, inputs: { source } })
      }
    );

    if (!githubResponse.ok) {
      const details = await githubResponse.text();
      console.error(JSON.stringify({
        level: "ERROR",
        event: "github_workflow_dispatch_failed",
        status: githubResponse.status,
        details: details.slice(0, 500)
      }));
      return {
        status: 502,
        payload: { ok: false, error: "GitHub workflow dispatch failed" }
      };
    }

    console.log(JSON.stringify({ level: "INFO", event: "refresh_queued", repository, workflowId }));
    return {
      status: 202,
      payload: { ok: true, message: "Refresh queued. GitHub Actions will update the data shortly." }
    };
  } catch (error) {
    console.error(JSON.stringify({
      level: "ERROR",
      event: "github_workflow_dispatch_error",
      error: error instanceof Error ? error.message : String(error)
    }));
    return { status: 502, payload: { ok: false, error: "Refresh request failed" } };
  }
}

module.exports = { authorizeRefresh, queueRefresh };
