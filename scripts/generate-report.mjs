import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";

const projectRoot = resolve(import.meta.dirname, "..");
const dataPath = resolve(projectRoot, "data", "deals.json");
const reportPath = resolve(projectRoot, "reports", "daily-deals.md");

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0
});

function summarizeBrand(brand) {
  return brand.items
    .map((item) => {
      const bestStore = [...item.stores].sort((left, right) => left.price - right.price)[0];
      const discountPct = Math.round(((bestStore.originalPrice - bestStore.price) / bestStore.originalPrice) * 100);
      const history = item.history.map((entry) => `${entry.date} - ${currencyFormatter.format(entry.price)}`).join("\n");

      return [
        `## ${item.name}`,
        "",
        `- Lowest price: ${currencyFormatter.format(bestStore.price)}`,
        `- Store: ${bestStore.name}`,
        `- Markdown: ${discountPct}% off`,
        `- Material: ${item.material}`,
        "",
        "Price history:",
        history,
        ""
      ].join("\n");
    })
    .join("\n");
}

function summarizeSingleBrand(payload) {
  return payload.items
    .map((item) => {
      const bestStore = [...item.offers].sort((left, right) => left.price - right.price)[0];
      const discountPct = Math.round(((bestStore.originalPrice - bestStore.price) / bestStore.originalPrice) * 100);
      const history = (item.history || []).map((entry) => `${entry.date} - ${currencyFormatter.format(entry.price)}`).join("\n");

      return [
        `## ${item.name}`,
        "",
        `- Lowest price: ${currencyFormatter.format(bestStore.price)}`,
        `- Store: ${bestStore.name}`,
        `- Markdown: ${discountPct}% off`,
        `- Release year: ${item.releaseYear ?? "Unknown"}`,
        "",
        "Price history:",
        history,
        ""
      ].join("\n");
    })
    .join("\n");
}

async function main() {
  const payload = JSON.parse(await readFile(dataPath, "utf8"));
  const sections = Array.isArray(payload.brands)
    ? payload.brands.map((brand) => `# ${brand.name}\n\n${summarizeBrand(brand)}`).join("\n")
    : `# ${payload.brand}\n\n${summarizeSingleBrand(payload)}`;
  const content = [
    "# Daily Dress Deals",
    "",
    `Generated: ${payload.lastUpdated}`,
    "",
    sections,
    ""
  ].join("\n");

  await mkdir(dirname(reportPath), { recursive: true });
  await writeFile(reportPath, content, "utf8");
  console.log(`Report written to ${reportPath}`);
}

main();
