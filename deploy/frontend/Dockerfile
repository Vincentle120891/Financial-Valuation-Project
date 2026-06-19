# =============================================================================
# FinGrid Frontend - Production Dockerfile
# Multi-stage build: Vite React app → Nginx static serving
# =============================================================================

# Stage 1: Build — compile React + Vite
FROM node:20-alpine AS builder

WORKDIR /app

# Vite bakes env vars at build time — must be passed as build arg
ARG VITE_API_URL=http://localhost:8000/api
ENV VITE_API_URL=$VITE_API_URL

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2: Production — Nginx serves static files
FROM nginx:alpine

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q --spider http://localhost:3000/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
