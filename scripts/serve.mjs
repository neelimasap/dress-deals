import { createReadStream } from "node:fs";
import { access } from "node:fs/promises";
import { createServer } from "node:http";
import { createRequire } from "node:module";
import { extname, normalize, resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const frontendRoot = resolve(root, "frontend");
const port = Number(process.env.PORT || 4173);
const require = createRequire(import.meta.url);
const { authorizeRefresh, queueRefresh } = require("../api/refresh-core.cjs");

const mimeTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".md": "text/markdown; charset=utf-8",
  ".svg": "image/svg+xml; charset=utf-8",
  ".webmanifest": "application/manifest+json; charset=utf-8"
};

const server = createServer(async (request, response) => {
  const urlPath = new URL(request.url, `http://${request.headers.host}`).pathname;

  if (request.method === "POST" && urlPath === "/api/refresh") {
    const authorization = authorizeRefresh(request, process.env.REFRESH_SECRET);
    if (!authorization.ok) {
      response.writeHead(authorization.status, { "Content-Type": "application/json" });
      response.end(JSON.stringify({ ok: false, error: authorization.error }));
      return;
    }
    const result = await queueRefresh({ source: "local-preview" });
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
