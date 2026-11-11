FROM node:26.13.1-alpine@sha256:f56092a5d85c32beef14de944aaa0110193ef1ae85205036c5d40d8aece58759 AS build
RUN npm install -g pnpm@12.15.0
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN --mount=type=cache,target=/root/.local/share/pnpm/store pnpm install --frozen-lockfile
COPY . .
ARG ORIGIN
RUN pnpm run build && pnpm prune --prod

FROM node:26.13.1-alpine@sha256:f56092a5d85c32beef14de944aaa0110193ef1ae85205036c5d40d8aece58759 AS runtime
# npm is unused at runtime and only adds scan findings (#49).
RUN rm -rf /usr/local/lib/node_modules/npm /usr/local/bin/npm /usr/local/bin/npx
ENV NODE_ENV=production PORT=3000 HOST=0.0.0.0
WORKDIR /app
COPY --from=build --chown=node:node /app/build ./build
COPY --from=build --chown=node:node /app/node_modules ./node_modules
COPY --from=build --chown=node:node /app/package.json ./
USER node
EXPOSE 3000
CMD ["node", "build"]