# NovaSight Frontend Dockerfile
# ==============================
# Multi-stage build for React/Vite application

# ============================================
# Base Stage
# ============================================
FROM node:20-alpine AS base

WORKDIR /app

# ============================================
# Development Stage
# ============================================
FROM base AS development

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source code
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Enable polling for file changes in Docker
ENV CHOKIDAR_USEPOLLING=true

# Start development server with HMR
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ============================================
# Builder Stage
# ============================================
FROM base AS builder

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source code
COPY . .

# Build production bundle
RUN npm run build

# ============================================
# Production Stage
# ============================================
FROM nginx:alpine AS production

# Copy custom nginx config
COPY docker/frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Add health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:80/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
