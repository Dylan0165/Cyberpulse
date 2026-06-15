# AWS ECR Public mirror of the Docker Hub official image — no pull rate limits.
FROM public.ecr.aws/docker/library/node:20-alpine AS base

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

FROM public.ecr.aws/docker/library/node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# next/font self-hosts the fonts into .next/static at build time.
COPY --from=base --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=base --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

CMD ["node", "server.js"]
