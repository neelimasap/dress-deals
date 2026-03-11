const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0
});

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  dateStyle: "medium",
  timeStyle: "short"
});

const compactDateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric"
});

let deferredPrompt;

async function loadDeals() {
  const response = await fetch("../data/deals.json");

  if (!response.ok) {
    throw new Error("Could not load deals data.");
  }

  return response.json();
}

<<<<<<< HEAD
function normalizeData(data) {
  if (Array.isArray(data.brands)) {
    return data.brands.flatMap((brand) =>
      brand.items.map((item) => ({
        brandName: brand.name,
        item: {
          ...item,
          stores: item.stores || item.offers || [],
          history: item.history || []
        }
      }))
    );
  }

  if (data.brand && Array.isArray(data.items)) {
    return data.items.map((item) => ({
      brandName: data.brand,
      item: {
        ...item,
        stores: item.offers || [],
        history: item.history || []
      }
    }));
  }

  return [];
}

=======
>>>>>>> 7cac992bb87289d5a5c4636070be74c4a79b99d3
function getItemSummary(brandName, item) {
  const sortedStores = [...item.stores].sort((left, right) => left.price - right.price);
  const bestStore = sortedStores[0];
  const discountPct = Math.round(((bestStore.originalPrice - bestStore.price) / bestStore.originalPrice) * 100);

  return {
    brandName,
    item,
    bestStore,
    discountPct
  };
}

function buildStats(items) {
  const totalTracked = items.length;
  const bestDiscount = Math.max(...items.map((entry) => entry.discountPct));
  const underSixHundred = items.filter((entry) => entry.bestStore.price < 600).length;

  return [
    { label: "Tracked styles", value: totalTracked },
    { label: "Best markdown", value: `${bestDiscount}%` },
    { label: "Under $600", value: underSixHundred }
  ];
}

function getImageUrl(item) {
  return item.imageUrl || null;
}

<<<<<<< HEAD
function getItemMeta(item) {
  if (item.releaseYear) {
    return `Released ${item.releaseYear}`;
  }

  if (item.silhouette || item.material) {
    return [item.silhouette, item.material].filter(Boolean).join(" / ");
  }

  return "Dress";
}

=======
>>>>>>> 7cac992bb87289d5a5c4636070be74c4a79b99d3
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
<<<<<<< HEAD
    <p class="best-deal-meta">${getItemMeta(bestDeal.item)}</p>
=======
    <p class="best-deal-meta">${bestDeal.item.silhouette} / ${bestDeal.item.material}</p>
>>>>>>> 7cac992bb87289d5a5c4636070be74c4a79b99d3
    <p class="best-deal-price">${currencyFormatter.format(bestDeal.bestStore.price)}</p>
    <p class="best-deal-meta">
      ${bestDeal.bestStore.name} / down ${bestDeal.discountPct}% from
      ${currencyFormatter.format(bestDeal.bestStore.originalPrice)}
    </p>
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
    const bars = node.querySelector(".sparkline");
    const labels = node.querySelector(".history-labels");
    const stores = node.querySelector(".store-list");
    const imageShell = node.querySelector(".deal-image-shell");
    const image = node.querySelector(".deal-image");
    const highestHistory = Math.max(...summary.item.history.map((entry) => entry.price));
    const imageUrl = getImageUrl(summary.item);

    node.querySelector(".brand-name").textContent = summary.brandName;
    node.querySelector(".item-name").textContent = summary.item.name;
    node.querySelector(".discount-pill").textContent = `${summary.discountPct}% off`;
<<<<<<< HEAD
    node.querySelector(".item-meta").textContent = getItemMeta(summary.item);
=======
    node.querySelector(".item-meta").textContent = `${summary.item.silhouette} / ${summary.item.material}`;
>>>>>>> 7cac992bb87289d5a5c4636070be74c4a79b99d3
    node.querySelector(".lowest-price").textContent = currencyFormatter.format(summary.bestStore.price);
    node.querySelector(".best-store").textContent = summary.bestStore.name;

    if (imageUrl) {
      image.src = imageUrl;
      image.alt = summary.item.name;
      imageShell.hidden = false;
      image.addEventListener("error", () => {
        imageShell.hidden = true;
      }, { once: true });
    }

    summary.item.history.forEach((entry) => {
      const bar = document.createElement("div");
      bar.className = "sparkline-bar";
      bar.style.height = `${Math.max(20, (entry.price / highestHistory) * 84)}px`;
      bar.title = `${compactDateFormatter.format(new Date(entry.date))}: ${currencyFormatter.format(entry.price)}`;
      bars.appendChild(bar);

      const label = document.createElement("span");
      label.textContent = compactDateFormatter.format(new Date(entry.date));
      labels.appendChild(label);
    });

    summary.item.stores
      .slice()
      .sort((left, right) => left.price - right.price)
      .forEach((store) => {
        const row = document.createElement("div");
        row.className = "store-row";
        row.innerHTML = `
          <div>
            <a href="${store.url}" target="_blank" rel="noreferrer">${store.name}</a>
            <div class="store-subtext">Updated ${dateFormatter.format(new Date(store.updatedAt))}</div>
          </div>
          <div>
            <strong>${currencyFormatter.format(store.price)}</strong>
            <div class="store-subtext">Was ${currencyFormatter.format(store.originalPrice)}</div>
          </div>
        `;
        stores.appendChild(row);
      });

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
    await navigator.serviceWorker.register("../service-worker.js");
  } catch (error) {
    console.error("Service worker registration failed", error);
  }
}

async function main() {
  try {
    const data = await loadDeals();
<<<<<<< HEAD
    const summaries = normalizeData(data)
      .map(({ brandName, item }) => getItemSummary(brandName, item))
      .sort((left, right) => right.discountPct - left.discountPct);

    if (!summaries.length) {
      throw new Error("No matching dress deals were found in the current dataset.");
    }

=======
    const summaries = data.brands
      .flatMap((brand) => brand.items.map((item) => getItemSummary(brand.name, item)))
      .sort((left, right) => right.discountPct - left.discountPct);
>>>>>>> 7cac992bb87289d5a5c4636070be74c4a79b99d3
    const bestDeal = summaries[0];

    renderBestDeal(bestDeal);
    renderStats(buildStats(summaries));
    renderDeals(summaries);
    document.querySelector("#last-updated").textContent = `Last updated ${dateFormatter.format(new Date(data.lastUpdated))}`;
  } catch (error) {
    document.querySelector("#deals-grid").innerHTML =
      `<article class="deal-card"><h3>Data unavailable</h3><p class="item-meta">${error.message}</p></article>`;
  }

  registerInstallPrompt();
  registerServiceWorker();
}

main();
