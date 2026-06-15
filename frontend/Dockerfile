# ============================================================
# NovaMind Frontend Dockerfile
# Stage 1: 构建 Vue3 SPA
# Stage 2: 用 node:serve 提供静态服务（无需 nginx）
# ============================================================

# ── Stage 1: Build ───────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# 接收构建参数
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# 使用淘宝镜像加速（中国服务器）
RUN npm config set registry https://registry.npmmirror.com

# 先复制 package 文件，利用层缓存
COPY package*.json ./

RUN npm ci --prefer-offline || npm install

# 复制源码并构建
COPY . .

RUN npm run build

# ── Stage 2: Serve ───────────────────────────────────────
FROM node:20-alpine AS runner

WORKDIR /app

# 安装 serve（轻量静态文件服务器，替代 nginx），指定淘宝镜像源加速
RUN npm config set registry https://registry.npmmirror.com && npm install -g serve

# 从 builder 阶段复制构建产物
COPY --from=builder /app/dist ./dist

EXPOSE 3000

# serve -s: SPA 模式（所有路由返回 index.html）
CMD ["serve", "-s", "dist", "-l", "3000"]
