FROM node:26-slim

# z-ai CLI needs bash + curl (curl also used by the healthcheck).
RUN apt-get update && apt-get install -y --no-install-recommends bash curl \
    && rm -rf /var/lib/apt/lists/*

# Install the z-ai CLI globally.
RUN npm install -g z-ai-web-dev-sdk

WORKDIR /app
COPY server.mjs .

EXPOSE 3031
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:3031/health || exit 1

CMD ["node", "server.mjs"]
