import { createReadStream } from "node:fs";
import { access } from "node:fs/promises";
import { createServer } from "node:http";
import { extname, normalize, resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const frontendRoot = resolve(root, "frontend");
const port = Number(process.env.PORT || 4173);

const mimeTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".md": "text/markdown; charset=utf-8",
  ".svg": "image/svg+xml; charset=utf-8",
  ".webmanifest": "application/manifest+json; charset=utf-8"
};

async function queueRefresh() {
  const token = process.env.GITHUB_TOKEN;
  const repository = process.env.GITHUB_REPOSITORY || "neelimasap/dress-deals";
  const workflowId = process.env.GITHUB_REFRESH_WORKFLOW || "daily-refresh.yml";
  const ref = process.env.GITHUB_REFRESH_REF || "main";

  if (!token) {
    return {
      status: 501,
      payload: {
        ok: false,
        error: "Missing GITHUB_TOKEN"
      }
    };
  }

  const [owner, repo] = repository.split("/");
  if (!owner || !repo) {
    return {
      status: 500,
      payload: {
        ok: false,
        error: "Invalid GITHUB_REPOSITORY"
      }
    };
  }

  try {
    const githubResponse = await fetch(
      `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflowId}/dispatches`,
      {
        method: "POST",
        headers: {
          Accept: "application/vnd.github+json",
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          "User-Agent": "dress-deals-refresh"
        },
        body: JSON.stringify({
          ref,
          inputs: {
            source: "local-preview"
          }
        })
      }
    );

    if (!githubResponse.ok) {
      const details = await githubResponse.text();
      return {
        status: githubResponse.status,
        payload: {
          ok: false,
          error: "GitHub workflow dispatch failed",
          details
        }
      };
    }

    return {
      status: 202,
      payload: {
        ok: true,
        message: "Refresh queued. GitHub Actions will update the data shortly."
      }
    };
  } catch (error) {
    return {
      status: 500,
      payload: {
        ok: false,
        error: "Refresh request failed",
        details: error instanceof Error ? error.message : String(error)
      }
    };
  }
}

const server = createServer(async (request, response) => {
  const urlPath = new URL(request.url, `http://${request.headers.host}`).pathname;

  if (request.method === "POST" && urlPath === "/api/refresh") {
    const result = await queueRefresh();
    response.writeHead(result.status, { "Content-Type": "application/json" });
    response.end(JSON.stringify(result.payload));
    return;
  }
  const candidate = urlPath === "/" ? "index.html" : urlPath.slice(1);
  const normalizedPath = normalize(candidate);
  const frontendPath = resolve(frontendRoot, normalizedPath);
  const rootPath = resolve(root, normalizedPath);

  if (!frontendPath.startsWith(frontendRoot) || !rootPath.startsWith(root)) {
    response.writeHead(403);
    response.end("Forbidden");
    return;
  }

  try {
    await access(rootPath);
    response.writeHead(200, {
      "Content-Type": mimeTypes[extname(rootPath)] || "application/octet-stream"
    });
    createReadStream(rootPath).pipe(response);
    return;
  } catch {
    try {
      await access(frontendPath);
      response.writeHead(200, {
        "Content-Type": mimeTypes[extname(frontendPath)] || "application/octet-stream"
      });
      createReadStream(frontendPath).pipe(response);
      return;
    } catch {
      const fallbackPath = resolve(root, "index.html");
      response.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
      createReadStream(fallbackPath).pipe(response);
    }
  }
});

server.listen(port, () => {
  console.log(`Dress Deals preview running at http://localhost:${port}`);
});
