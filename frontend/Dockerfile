# ── Stage 1: Builder (production build) ──
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency manifests first for layer caching
COPY package.json package-lock.json* ./

RUN npm ci --ignore-scripts

# Copy source and build
COPY . .
RUN npm run build

# ── Stage 2: Dev server (default target for compose) ──
FROM node:20-alpine AS dev

WORKDIR /app

# Create non-root user
RUN addgroup -g 1001 -S sentinel && \
    adduser -u 1001 -S sentinel -G sentinel

# Copy dependency manifests and install
COPY package.json package-lock.json* ./
RUN npm ci --ignore-scripts && \
    chown -R sentinel:sentinel /app

# Copy source code
COPY --chown=sentinel:sentinel . .

USER sentinel

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]

# ── Stage 3: Production (static files served by nginx) ──
FROM nginx:1.27-alpine AS production

COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
