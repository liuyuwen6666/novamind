# ==========================================
# Stage 1: Build the Vue 3 Frontend SPA
# ==========================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# Copy dependency files first for caching benefits
COPY frontend/package*.json ./
RUN npm ci

# Copy frontend source files
COPY frontend/ ./

# Build the frontend. The static assets will be output
# to ../backend/static (as configured in vite.config.js)
RUN npm run build

# ==========================================
# Stage 2: Create the final lightweight image
# ==========================================
FROM python:3.11-slim
WORKDIR /app

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install runtime dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application files
COPY backend/app/ ./app/

# Copy built frontend assets from the previous stage
COPY --from=frontend-builder /app/backend/static ./static

# Expose FastAPI default port
EXPOSE 8000

# Set environment variables for FastAPI
ENV APP_HOST=0.0.0.0
ENV APP_PORT=8000

# Start Uvicorn web server
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
