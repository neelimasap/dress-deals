const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0
});

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  dateStyle: "medium",
  timeStyle: "short"
});

let deferredPrompt;

function formatSourceType(value) {
  const labels = {
    retail: "Retail",
    aggregator: "Aggregator",
    resale: "Resale"
  };
  return labels[value] || "Aggregator";
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function normalizeStoreName(name) {
  return String(name || "").trim().toLowerCase();
}

function currency(value) {
  return currencyFormatter.format(value || 0);
}

async function loadDeals() {
  const response = await fetch("/data/deals.json");
  if (!response.ok) {
    throw new Error("Could not load deals data.");
  }
  return response.json();
}

function normalizeData(data) {
  if (Array.isArray(data.brands)) {
    return data.brands.map((brand) => ({
      name: brand.name,
      items: (brand.items || []).map((item) => ({
        ...item,
        stores: item.stores || item.offers || []
      }))
    }));
  }

  if (data.brand && Array.isArray(data.items)) {
    return [{
      name: data.brand,
      items: data.items.map((item) => ({
        ...item,
        stores: item.offers || []
      }))
    }];
  }

  return [];
}

function getItemMeta(item) {
  if (item.releaseYear) {
    return `Released ${item.releaseYear}`;
  }
  if (item.silhouette || item.material) {
    return [item.silhouette, item.material].filter(Boolean).join(" / ");
  }
  return "Dress entity";
}

function buildBrandOptions(brands) {
  return brands.map((brand) => brand.name).sort((left, right) => left.localeCompare(right));
}

function buildStoreOptions(entities) {
  const stores = new Map();
  entities.forEach((entity) => {
    const key = normalizeStoreName(entity.bestStore.name);
    if (!key || stores.has(key)) {
      return;
    }
    stores.set(key, entity.bestStore.name);
  });
  return [...stores.entries()]
    .sort((left, right) => left[1].localeCompare(right[1]))
    .map(([, label]) => label);
}

function buildSourceOptions(entities) {
  return [...new Set(entities.map((entity) => entity.bestStore.sourceCategory || "aggregator"))]
    .sort((left, right) => formatSourceType(left).localeCompare(formatSourceType(right)))
    .map((value) => ({ value, label: formatSourceType(value) }));
}

function getLowestSeen(item) {
  const prices = [];
  for (const offer of item.stores || []) {
    if (Number.isFinite(offer.price)) {
      prices.push(Number(offer.price));
    }
  }
  for (const entry of item.history || []) {
    if (Number.isFinite(entry.price)) {
      prices.push(Number(entry.price));
    }
  }
  return prices.length ? Math.min(...prices) : null;
}

function getBuyNowScore(bestStore, lowestSeen, coverageCount, hasDiscount, discountPct) {
  if (!hasDiscount) {
    return null;
  }
  let score = 52;
  if (hasDiscount) {
    score += Math.min(discountPct, 35);
  }
  if (lowestSeen !== null && bestStore.price <= lowestSeen) {
    score += 10;
  }
  score += Math.min(coverageCount * 4, 16);

  if ((bestStore.sourceCategory || "aggregator") === "retail") {
    score += 8;
  } else if ((bestStore.sourceCategory || "aggregator") === "resale") {
    score -= 8;
  }

  return clamp(Math.round(score), 1, 99);
}

function getRecommendation(score, bestStore, lowestSeen, hasDiscount) {
  if (!hasDiscount) {
    return "Watch";
  }
  if ((bestStore.sourceCategory || "aggregator") === "retail" && lowestSeen !== null && bestStore.price <= lowestSeen) {
    return "Buy now";
  }
  if (score >= 88) {
    return "Buy now";
  }
  if (score >= 72) {
    return "Strong contender";
  }
  return "Watch";
}

function getEntitySummary(brandName, item) {
  const stores = [...(item.stores || [])].sort((left, right) => left.price - right.price);
  const bestStore = stores[0];
  const lowestSeen = getLowestSeen(item);
  const hasDiscount = bestStore.originalPrice > bestStore.price;
  const discountPct = hasDiscount
    ? Math.round(((bestStore.originalPrice - bestStore.price) / bestStore.originalPrice) * 100)
    : 0;
  const buyNowScore = getBuyNowScore(bestStore, lowestSeen, stores.length, hasDiscount, discountPct);
  const recommendation = getRecommendation(buyNowScore, bestStore, lowestSeen, hasDiscount);
  const searchText = [
    brandName,
    item.name,
    getItemMeta(item),
    bestStore.name,
    bestStore.sourceCategory
  ].join(" ").toLowerCase();

  return {
    brandName,
    item,
    bestStore,
    stores,
    hasDiscount,
    discountPct,
    lowestSeen,
    buyNowScore,
    recommendation,
    searchText
  };
}

function buildStats(allEntities, visibleEntities) {
  const buyNowCount = visibleEntities.filter((entity) => entity.recommendation === "Buy now").length;
  const bestDiscount = allEntities.length ? Math.max(...allEntities.map((entity) => entity.discountPct)) : 0;
  const scoredEntities = visibleEntities.filter((entity) => Number.isFinite(entity.buyNowScore));
  const averageScore = scoredEntities.length
    ? Math.round(scoredEntities.reduce((sum, entity) => sum + entity.buyNowScore, 0) / scoredEntities.length)
    : 0;

  return [
    { label: "Dress entities", value: allEntities.length },
    { label: "Buy now calls", value: buyNowCount },
    { label: "Avg buy score", value: averageScore },
    { label: "Best markdown", value: `${bestDiscount}%` }
  ];
}

function getImageUrl(item) {
  return item.imageUrl || null;
}

function renderBestDeal(entity) {
  const host = document.querySelector("#best-deal");
  const imageMarkup = getImageUrl(entity.item)
    ? `
      <div class="best-deal-image-shell">
        <img class="best-deal-image" src="${entity.item.imageUrl}" alt="${entity.item.name}" loading="lazy" />
      </div>
    `
    : "";

  const lowestSeenCopy = entity.lowestSeen !== null
    ? `Lowest seen: ${currency(entity.lowestSeen)}`
    : "Lowest seen: still building history";
  const signalCopy = entity.buyNowScore === null
    ? `Signal: Watch - no confirmed discount yet - ${formatSourceType(entity.bestStore.sourceCategory)}`
    : `Signal: ${entity.recommendation} - score ${entity.buyNowScore}/99 - ${formatSourceType(entity.bestStore.sourceCategory)}`;

  host.innerHTML = `
    ${imageMarkup}
    <p class="brand-name">${entity.brandName}</p>
    <h2>${entity.item.name}</h2>
    <p class="best-deal-meta">${getItemMeta(entity.item)}</p>
    <p class="best-deal-meta">Best current buy: ${entity.bestStore.name} at ${currency(entity.bestStore.price)}</p>
    <p class="best-deal-meta">${lowestSeenCopy}</p>
    <p class="best-deal-meta">${signalCopy}</p>
    <a class="button button-secondary best-deal-link" href="${entity.bestStore.url}" target="_blank" rel="noreferrer">
      Buy From ${entity.bestStore.name}
    </a>
  `;

  const image = host.querySelector(".best-deal-image");
  if (image) {
    image.addEventListener("error", () => {
      image.closest(".best-deal-image-shell")?.remove();
    }, { once: true });
  }
}

function renderStats(stats) {
  const statsGrid = document.querySelector("#stats-grid");
  statsGrid.replaceChildren(
    ...stats.map((stat) => {
      const article = document.createElement("article");
      article.innerHTML = `<p class="eyebrow">${stat.label}</p><strong>${stat.value}</strong>`;
      return article;
    })
  );
}

function populateCard(node, entity) {
  const imageShell = node.querySelector(".deal-image-shell");
  const image = node.querySelector(".deal-image");
  const imageUrl = getImageUrl(entity.item);

  node.querySelector(".brand-name").textContent = entity.brandName;
  node.querySelector(".item-name").textContent = entity.item.name;
  const discountPill = node.querySelector(".discount-pill");
  if (entity.hasDiscount) {
    discountPill.textContent = `${entity.discountPct}% off`;
  } else {
    discountPill.remove();
  }

  const offerStore = node.querySelector(".offer-store");
  offerStore.innerHTML = `<a href="${entity.bestStore.url}" target="_blank" rel="noreferrer">${entity.bestStore.name}</a>`;
  node.querySelector(".offer-secondary").textContent = entity.lowestSeen !== null && entity.lowestSeen < entity.bestStore.price
    ? `Lowest seen ${currency(entity.lowestSeen)}`
    : "";
  node.querySelector(".offer-price").textContent = currency(entity.bestStore.price);
  node.querySelector(".offer-original").textContent = entity.hasDiscount
    ? `Was ${currency(entity.bestStore.originalPrice)}`
    : "";

  if (imageUrl) {
    const imageLink = document.createElement("a");
    imageLink.href = entity.bestStore.url;
    imageLink.target = "_blank";
    imageLink.rel = "noreferrer";
    image.src = imageUrl;
    image.alt = entity.item.name;
    imageShell.appendChild(imageLink);
    imageLink.appendChild(image);
    imageShell.hidden = false;
    image.addEventListener("error", () => {
      imageShell.hidden = true;
    }, { once: true });
  }
}

function renderEntityGrid(selector, entities) {
  const grid = document.querySelector(selector);
  const template = document.querySelector("#deal-card-template");
  const cards = entities.map((entity) => {
    const node = template.content.cloneNode(true);
    populateCard(node, entity);
    return node.querySelector(".deal-card");
  });
  grid.replaceChildren(...cards);
}

function registerInstallPrompt() {
  const installButton = document.querySelector("#install-button");
  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    deferredPrompt = event;
    installButton.hidden = false;
  });

  installButton.addEventListener("click", async () => {
    if (!deferredPrompt) {
      return;
    }
    deferredPrompt.prompt();
    await deferredPrompt.userChoice;
    deferredPrompt = undefined;
    installButton.hidden = true;
  });
}

async function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) {
    return;
  }

  try {
    if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
      const registrations = await navigator.serviceWorker.getRegistrations();
      await Promise.all(registrations.map((registration) => registration.unregister()));
      if ("caches" in window) {
        const cacheNames = await caches.keys();
        await Promise.all(cacheNames.map((cacheName) => caches.delete(cacheName)));
      }
      return;
    }
    await navigator.serviceWorker.register("/service-worker.js");
  } catch (error) {
    console.error("Service worker registration failed", error);
  }
}

async function main() {
  try {
    const data = await loadDeals();
    const brands = normalizeData(data);
    if (!brands.length) {
      throw new Error("No dress entities were found in the current dataset.");
    }

    const brandFilter = document.querySelector("#brand-filter");
    const sourceFilter = document.querySelector("#source-filter");
    const priceFilter = document.querySelector("#price-filter");
    const storeFilter = document.querySelector("#store-filter");
    const intentForm = document.querySelector("#intent-form");
    const intentInput = document.querySelector("#intent-input");
    const heading = document.querySelector(".section-heading h2");
    const emptyState = document.querySelector("#empty-state");

    brandFilter.replaceChildren(
      ...[
        (() => {
          const option = document.createElement("option");
          option.value = "";
          option.textContent = "All brands";
          return option;
        })(),
        ...buildBrandOptions(brands).map((brand) => {
          const option = document.createElement("option");
          option.value = brand;
          option.textContent = brand;
          return option;
        })
      ]
    );
    if (brands.length === 1) {
      brandFilter.value = brands[0].name;
    }

    function getEntities(selectedBrand) {
      const visibleBrands = selectedBrand
        ? brands.filter((brand) => brand.name === selectedBrand)
        : brands;

      return visibleBrands
        .flatMap((brand) => brand.items.map((item) => getEntitySummary(brand.name, item)))
        .sort((left, right) => {
          if (right.buyNowScore !== left.buyNowScore) {
            return right.buyNowScore - left.buyNowScore;
          }
          return left.bestStore.price - right.bestStore.price;
        });
    }

    function syncStoreOptions(entities) {
      const previousSelection = storeFilter.value;
      storeFilter.replaceChildren(
        ...[
          (() => {
            const option = document.createElement("option");
            option.value = "";
            option.textContent = "All stores";
            return option;
          })(),
          ...buildStoreOptions(entities).map((store) => {
            const option = document.createElement("option");
            option.value = store;
            option.textContent = store;
            return option;
          })
        ]
      );
      const hasPreviousSelection = [...storeFilter.options].some((option) => option.value === previousSelection);
      storeFilter.value = hasPreviousSelection ? previousSelection : "";
    }

    function syncSourceOptions(entities) {
      const previousSelection = sourceFilter.value;
      sourceFilter.replaceChildren(
        ...[
          (() => {
            const option = document.createElement("option");
            option.value = "";
            option.textContent = "All source types";
            return option;
          })(),
          ...buildSourceOptions(entities).map((source) => {
            const option = document.createElement("option");
            option.value = source.value;
            option.textContent = source.label;
            return option;
          })
        ]
      );
      const hasPreviousSelection = [...sourceFilter.options].some((option) => option.value === previousSelection);
      sourceFilter.value = hasPreviousSelection ? previousSelection : "";
    }

    function applyFilter() {
      const selectedBrand = brandFilter.value;
      const allEntities = getEntities(selectedBrand);
      syncStoreOptions(allEntities);
      syncSourceOptions(allEntities);

      const intent = intentInput.value.trim().toLowerCase();
      const maxPrice = priceFilter.value ? Number(priceFilter.value) : Infinity;
      const selectedStore = normalizeStoreName(storeFilter.value);
      const selectedSourceType = sourceFilter.value;

      const visible = allEntities.filter((entity) =>
        entity.bestStore.price <= maxPrice
        && (!selectedStore || normalizeStoreName(entity.bestStore.name) === selectedStore)
        && (!selectedSourceType || (entity.bestStore.sourceCategory || "aggregator") === selectedSourceType)
        && (!intent || entity.searchText.includes(intent))
      );

      heading.textContent = selectedBrand
        ? `${selectedBrand} best buys`
        : "Best buys across the market";

      const heroEntity = visible[0] || allEntities[0];
      if (heroEntity) {
        renderBestDeal(heroEntity);
      } else {
        document.querySelector("#best-deal").innerHTML =
          `<p class="best-deal-meta">No dress entities match that buying brief yet.</p>`;
      }

      renderStats(buildStats(allEntities, visible));
      renderEntityGrid("#recommendations-grid", visible.slice(0, 3));
      renderEntityGrid("#deals-grid", visible);
      emptyState.hidden = visible.length > 0;
    }

    intentForm.addEventListener("submit", (event) => {
      event.preventDefault();
      applyFilter();
    });
    intentInput.addEventListener("search", applyFilter);
    brandFilter.addEventListener("change", applyFilter);
    sourceFilter.addEventListener("change", applyFilter);
    priceFilter.addEventListener("change", applyFilter);
    storeFilter.addEventListener("change", applyFilter);
    applyFilter();

    document.querySelector("#last-updated").textContent = `Last refreshed ${dateFormatter.format(new Date(data.lastUpdated))}`;
  } catch (error) {
    document.querySelector("#deals-grid").innerHTML =
      `<article class="deal-card"><h3>Data unavailable</h3><p class="item-meta">${error.message}</p></article>`;
  }

  registerInstallPrompt();
  registerServiceWorker();
}

main();
