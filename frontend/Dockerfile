# Frontend Dockerfile — production multi-stage build
# Stage 1: Build React app with Vite
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first (layer caching)
COPY package.json package-lock.json* ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# Stage 2: Serve static build with Nginx
FROM nginx:1.25-alpine

# Copy the production build output
COPY --from=builder /app/dist /usr/share/nginx/html

# Replace default nginx config with our SPA + proxy config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
