#!/bin/bash
set -e

# ============================================================
# PostgreSQL 外网访问配置
# 在 pg_hba.conf 中添加规则，允许通过密码认证的外部连接
# ============================================================

PG_HBA=/var/lib/postgresql/data/pg_hba.conf

# ── 信号转发：确保 docker stop 能优雅关闭 postgres ──
cleanup() {
    echo "[entrypoint] Received shutdown signal, forwarding to postgres..."
    kill -TERM "$POSTGRES_PID" 2>/dev/null
    wait "$POSTGRES_PID"
    exit 0
}
trap cleanup SIGTERM SIGINT

add_external_access() {
    if [ -f "$PG_HBA" ]; then
        # 如果已有该规则则先删除，避免重复
        sed -i '/^host\s\+all\s\+all\s\+0\.0\.0\.0\/0/d' "$PG_HBA"
        # 添加规则：允许任意 IP 通过 md5 密码认证访问所有数据库
        echo "host all all 0.0.0.0/0 md5" >> "$PG_HBA"
        echo "[entrypoint] Added external access rule to pg_hba.conf"
    fi
}

# ── 1. 如果 pg_hba.conf 已存在（非首次启动），直接添加规则 ──
add_external_access

# ── 2. 交给原始 entrypoint 处理 PostgreSQL 初始化/启动 ──
#     首次启动时，docker-entrypoint.sh 会初始化数据库（创建 pg_hba.conf）
#     然后启动 postgres。我们用后台方式启动，待就绪后再检查规则
docker-entrypoint.sh "$@" &

POSTGRES_PID=$!

# ── 3. 等待 PostgreSQL 就绪，首次启动时补充规则 ──
for i in $(seq 1 60); do
    if pg_isready -U postgres -h localhost >/dev/null 2>&1; then
        # 检查规则是否存在（首次启动时 pg_hba.conf 刚被创建）
        if [ -f "$PG_HBA" ] && ! grep -q "host all all 0.0.0.0/0" "$PG_HBA" 2>/dev/null; then
            echo "host all all 0.0.0.0/0 md5" >> "$PG_HBA"
            # 重新加载配置，无需重启
            psql -U postgres -c "SELECT pg_reload_conf();" 2>/dev/null || true
            echo "[entrypoint] Added external access rule after first-time init"
        fi
        break
    fi
    sleep 1
done

# ── 4. 保持容器运行 ──
wait $POSTGRES_PID
