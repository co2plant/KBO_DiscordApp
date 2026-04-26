FROM node:20-slim

ENV NODE_ENV=production

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        chromium \
        chromium-driver \
        fonts-nanum \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package*.json /app/
RUN npm ci --omit=dev

COPY . /app

CMD ["node", "index.js"]
