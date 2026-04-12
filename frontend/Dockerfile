FROM node:20-alpine AS base
WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm ci --ignore-scripts

# Development stage
FROM base AS dev
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

# Build stage
FROM base AS builder
# NEXT_PUBLIC_* vars are inlined into the JS bundle at build time — they must be
# declared as ARG + ENV here so `npm run build` can embed them.
ARG NEXT_PUBLIC_SENTRY_DSN=""
ARG NEXT_PUBLIC_SENTRY_ENVIRONMENT="production"
ENV NEXT_PUBLIC_SENTRY_DSN=$NEXT_PUBLIC_SENTRY_DSN
ENV NEXT_PUBLIC_SENTRY_ENVIRONMENT=$NEXT_PUBLIC_SENTRY_ENVIRONMENT
COPY . .
RUN npm run build

# Production stage
FROM node:20-alpine AS production
RUN apk update && apk upgrade --no-cache
WORKDIR /app
ENV NODE_ENV=production

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy standalone output with correct ownership
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
# next-intl loads messages at runtime via dynamic import — must be present in the image
COPY --from=builder --chown=nextjs:nodejs /app/messages ./messages

USER nextjs

EXPOSE 3000
ENV HOSTNAME="0.0.0.0"
CMD ["node", "server.js"]
