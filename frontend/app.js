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

async function loadDeals() {
  const response = await fetch("../data/deals.json");

  if (!response.ok) {
    throw new Error("Could not load deals data.");
  }

  return response.json();
}

function normalizeData(data) {
  if (Array.isArray(data.brands)) {
    return data.brands.flatMap((brand) =>
      brand.items.map((item) => ({
        brandName: brand.name,
        item: {
          ...item,
          stores: item.stores || item.offers || []
        }
      }))
    );
  }

  if (data.brand && Array.isArray(data.items)) {
    return data.items.map((item) => ({
      brandName: data.brand,
      item: {
        ...item,
        stores: item.offers || []
      }
    }));
  }

  return [];
}

function getItemSummary(brandName, item) {
  const sortedStores = [...item.stores].sort((left, right) => left.price - right.price);
  const bestStore = sortedStores[0];
  const hasDiscount = bestStore.originalPrice > bestStore.price;
  const discountPct = hasDiscount
    ? Math.round(((bestStore.originalPrice - bestStore.price) / bestStore.originalPrice) * 100)
    : 0;

  return {
    brandName,
    item,
    bestStore,
    discountPct,
    hasDiscount
  };
}

function buildStats(allSummaries, visibleSummaries) {
  const bestDiscount = Math.max(...allSummaries.map((entry) => entry.discountPct));

  return [
    { label: "Tracked styles", value: allSummaries.length },
    { label: "Best markdown", value: `${bestDiscount}%` },
    { label: "Showing now", value: visibleSummaries.length }
  ];
}

function getImageUrl(item) {
  return item.imageUrl || null;
}

function normalizeStoreName(name) {
  return String(name || "").trim().toLowerCase();
}

function buildStoreOptions(allSummaries) {
  const stores = new Map();

  allSummaries.forEach((summary) => {
    const key = normalizeStoreName(summary.bestStore.name);
    if (!key || stores.has(key)) {
      return;
    }
    stores.set(key, summary.bestStore.name);
  });

  return [...stores.entries()]
    .sort((left, right) => left[1].localeCompare(right[1]))
    .map(([, label]) => label);
}

function getItemMeta(item) {
  if (item.releaseYear) {
    return `Released ${item.releaseYear}`;
  }

  if (item.silhouette || item.material) {
    return [item.silhouette, item.material].filter(Boolean).join(" / ");
  }

  return "Dress";
}

function renderBestDeal(bestDeal) {
  const host = document.querySelector("#best-deal");
  const imageMarkup = getImageUrl(bestDeal.item)
    ? `
      <div class="best-deal-image-shell">
        <img class="best-deal-image" src="${bestDeal.item.imageUrl}" alt="${bestDeal.item.name}" loading="lazy" />
      </div>
    `
    : "";

  host.innerHTML = `
    ${imageMarkup}
    <p class="brand-name">${bestDeal.brandName}</p>
    <h2>${bestDeal.item.name}</h2>
    <p class="best-deal-meta">${getItemMeta(bestDeal.item)}</p>
    <p class="best-deal-meta">
      ${bestDeal.hasDiscount
        ? `Best markdown today: ${bestDeal.discountPct}% off at ${bestDeal.bestStore.name}`
        : `Best available price today: ${bestDeal.bestStore.name}`}
    </p>
    <a class="button button-secondary best-deal-link" href="${bestDeal.bestStore.url}" target="_blank" rel="noreferrer">
      View top pick
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

function renderDeals(items) {
  const grid = document.querySelector("#deals-grid");
  const template = document.querySelector("#deal-card-template");

  const cards = items.map((summary) => {
    const node = template.content.cloneNode(true);
    const card = node.querySelector(".deal-card");
    const imageShell = node.querySelector(".deal-image-shell");
    const image = node.querySelector(".deal-image");
    const imageUrl = getImageUrl(summary.item);

    node.querySelector(".brand-name").textContent = summary.brandName;
    node.querySelector(".item-name").textContent = summary.item.name;
    const discountPill = node.querySelector(".discount-pill");
    if (summary.hasDiscount) {
      discountPill.textContent = `${summary.discountPct}% off`;
    } else {
      discountPill.remove();
    }
    node.querySelector(".item-meta").textContent = getItemMeta(summary.item);
    const offerStore = node.querySelector(".offer-store");
    offerStore.innerHTML = `<a href="${summary.bestStore.url}" target="_blank" rel="noreferrer">${summary.bestStore.name}</a>`;
    node.querySelector(".offer-price").textContent = currencyFormatter.format(summary.bestStore.price);
    node.querySelector(".offer-updated").textContent = `Updated ${dateFormatter.format(new Date(summary.bestStore.updatedAt))}`;
    node.querySelector(".offer-original").textContent =
      summary.hasDiscount
        ? `Was ${currencyFormatter.format(summary.bestStore.originalPrice)}`
        : "";
    if (imageUrl) {
      const imageLink = document.createElement("a");
      imageLink.href = summary.bestStore.url;
      imageLink.target = "_blank";
      imageLink.rel = "noreferrer";
      image.src = imageUrl;
      image.alt = summary.item.name;
      imageShell.appendChild(imageLink);
      imageLink.appendChild(image);
      imageShell.hidden = false;
      image.addEventListener("error", () => {
        imageShell.hidden = true;
      }, { once: true });
    }

    return card;
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

    await navigator.serviceWorker.register("../service-worker.js");
  } catch (error) {
    console.error("Service worker registration failed", error);
  }
}

async function main() {
  try {
    const data = await loadDeals();
    const allSummaries = normalizeData(data)
      .map(({ brandName, item }) => getItemSummary(brandName, item))
      .sort((left, right) => {
        if (right.discountPct !== left.discountPct) {
          return right.discountPct - left.discountPct;
        }
        return left.bestStore.price - right.bestStore.price;
      });

    if (!allSummaries.length) {
      throw new Error("No matching dress deals were found in the current dataset.");
    }

    const priceFilter = document.querySelector("#price-filter");
    const storeFilter = document.querySelector("#store-filter");

    storeFilter.replaceChildren(
      ...[
        (() => {
          const option = document.createElement("option");
          option.value = "";
          option.textContent = "All stores";
          return option;
        })(),
        ...buildStoreOptions(allSummaries).map((store) => {
          const option = document.createElement("option");
          option.value = store;
          option.textContent = store;
          return option;
        })
      ]
    );

    function applyFilter() {
      const maxPrice = priceFilter.value ? Number(priceFilter.value) : Infinity;
      const selectedStore = normalizeStoreName(storeFilter.value);
      const visible = allSummaries.filter((summary) =>
        summary.bestStore.price <= maxPrice
        && (!selectedStore || normalizeStoreName(summary.bestStore.name) === selectedStore)
      );
      const bestDeal = visible[0] || allSummaries[0];
      renderBestDeal(bestDeal);
      renderStats(buildStats(allSummaries, visible));
      renderDeals(visible);
    }

    priceFilter.addEventListener("change", applyFilter);
    storeFilter.addEventListener("change", applyFilter);
    applyFilter();

    document.querySelector("#last-updated").textContent = `Last updated ${dateFormatter.format(new Date(data.lastUpdated))}`;
  } catch (error) {
    document.querySelector("#deals-grid").innerHTML =
      `<article class="deal-card"><h3>Data unavailable</h3><p class="item-meta">${error.message}</p></article>`;
  }

  registerInstallPrompt();
  registerServiceWorker();
}

main();
