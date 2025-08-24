# Multi-stage build for React frontend
FROM node:18-alpine as builder

# Set build arguments
ARG REACT_APP_API_URL=http://localhost:8000
ARG REACT_APP_WS_URL=ws://localhost:8000
ARG BUILD_ENV=production

# Set work directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production --silent

# Copy source code
COPY . .

# Set environment variables for build
ENV REACT_APP_API_URL=${REACT_APP_API_URL}
ENV REACT_APP_WS_URL=${REACT_APP_WS_URL}
ENV NODE_ENV=production
ENV GENERATE_SOURCEMAP=false

# Build the application
RUN npm run build

# Production stage with Nginx
FROM nginx:alpine as production

# Install curl for health checks
RUN apk add --no-cache curl

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built React app from builder stage
COPY --from=builder /app/build /usr/share/nginx/html

# Copy environment variable injection script
COPY <<'EOF' /docker-entrypoint.d/30-inject-env.sh
#!/bin/sh
set -eu

# Replace environment variables in JavaScript files
envsubst "$(printf '${%s} ' $(env | cut -d'=' -f1))" < /usr/share/nginx/html/static/js/main.*.js > /tmp/main.js
mv /tmp/main.js /usr/share/nginx/html/static/js/main.*.js

# Replace environment variables in index.html
envsubst "$(printf '${%s} ' $(env | cut -d'=' -f1))" < /usr/share/nginx/html/index.html > /tmp/index.html
mv /tmp/index.html /usr/share/nginx/html/index.html

echo "Environment variables injected into React build"
EOF

RUN chmod +x /docker-entrypoint.d/30-inject-env.sh

# Create non-root user for nginx
RUN addgroup -g 1000 -S appuser \
    && adduser -S -D -H -u 1000 -h /usr/share/nginx/html -s /sbin/nologin -G appuser -g appuser appuser \
    && chown -R appuser:appuser /usr/share/nginx/html \
    && chmod -R 755 /usr/share/nginx/html

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]

# Development stage (optional)
FROM node:18-alpine as development

# Set work directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install all dependencies including dev dependencies
RUN npm install

# Copy source code
COPY . .

# Expose port
EXPOSE 3000

# Start development server
CMD ["npm", "start"]