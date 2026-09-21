FROM node:20-bookworm-slim

RUN apt-get update \
    && apt-get install --yes --no-install-recommends python3 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package.json ./
COPY api ./api
COPY config ./config
COPY data ./data
COPY frontend ./frontend
COPY icons ./icons
COPY scripts ./scripts
COPY index.html manifest.webmanifest service-worker.js vercel.json ./

ENV NODE_ENV=production
ENV PORT=4173

EXPOSE 4173

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:4173/data/deals.json').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"

CMD ["node", "scripts/serve.mjs"]
