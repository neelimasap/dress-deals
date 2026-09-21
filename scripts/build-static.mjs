import { cp, copyFile, mkdir, rm } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const output = resolve(root, "public");

await rm(output, { recursive: true, force: true });
await mkdir(output, { recursive: true });

for (const directory of ["data", "frontend", "icons", "reports"]) {
  await cp(resolve(root, directory), resolve(output, directory), { recursive: true });
}

for (const file of ["index.html", "manifest.webmanifest", "service-worker.js"]) {
  await copyFile(resolve(root, file), resolve(output, file));
}

console.log(`Static deployment assembled at ${output}`);
