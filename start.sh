#!/bin/bash
# ============================================================
# 自动盖章系统 — 一键启动脚本
# ============================================================
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
LOG_DIR="$PROJECT_DIR/logs"
PID_DIR="$PROJECT_DIR/.pids"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

mkdir -p "$LOG_DIR" "$PID_DIR"

log()  { echo -e "${GREEN}[$(date +%H:%M:%S)]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date +%H:%M:%S)]${NC} $1"; }
err()  { echo -e "${RED}[$(date +%H:%M:%S)]${NC} $1"; }

# ==============================
# 1. 清理旧进程
# ==============================
log "清理旧进程..."
kill $(cat "$PID_DIR/backend.pid" 2>/dev/null) 2>/dev/null || true
kill $(cat "$PID_DIR/static.pid" 2>/dev/null) 2>/dev/null || true
kill $(cat "$PID_DIR/tunnel.pid" 2>/dev/null) 2>/dev/null || true
fuser -k 8000/tcp 2>/dev/null || true
fuser -k 5173/tcp 2>/dev/null || true
sleep 1

# ==============================
# 2. 启动后端
# ==============================
log "启动 FastAPI 后端 (port 8000)..."
cd "$BACKEND_DIR"
PYTHONPATH="$BACKEND_DIR" python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 \
    > "$LOG_DIR/backend.log" 2>&1 &
echo $! > "$PID_DIR/backend.pid"
sleep 3

if curl -s -o /dev/null http://localhost:8000/api/v1/health 2>/dev/null; then
    log "  后端启动成功 ✅"
else
    err "  后端启动失败，查看日志: $LOG_DIR/backend.log"
fi

# ==============================
# 3. 启动静态服务 + API 代理
# ==============================
log "启动静态服务 (port 5173)..."
cd "$PROJECT_DIR"
python3 serve.py \
    > "$LOG_DIR/static.log" 2>&1 &
echo $! > "$PID_DIR/static.pid"
sleep 2

if curl -s -o /dev/null http://localhost:5173 2>/dev/null; then
    log "  静态服务启动成功 ✅"
else
    err "  静态服务启动失败，查看日志: $LOG_DIR/static.log"
fi

# ==============================
# 4. 启动 serveo.net SSH 隧道 (固定域名)
# ==============================
FIXED_URL="https://autostamp.serveo.net"
echo "$FIXED_URL" > "$PROJECT_DIR/.public_url"

log "启动 serveo.net 隧道 (固定域名: $FIXED_URL)..."
bash "$PROJECT_DIR/tunnel_watchdog.sh" \
    > "$LOG_DIR/tunnel.log" 2>&1 &
echo $! > "$PID_DIR/tunnel.pid"
sleep 8

if curl -s -o /dev/null "$FIXED_URL" 2>/dev/null; then
    log "  隧道已建立 ✅"
    TUNNEL_URL="$FIXED_URL"
else
    warn "  隧道连接中，稍后访问: $FIXED_URL"
    TUNNEL_URL="$FIXED_URL"
fi

# ==============================
# 5. 输出汇总
# ==============================
echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║        自动盖章系统 — 启动完成                ║${NC}"
echo -e "${CYAN}╠════════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║${NC}  前端 (本地):  ${GREEN}http://localhost:5173${NC}"
echo -e "${CYAN}║${NC}  API   (本地):  ${GREEN}http://localhost:8000/docs${NC}"
echo -e "${CYAN}║${NC}  前端 (外网):  ${GREEN}${TUNNEL_URL}${NC}"
echo -e "${CYAN}║${NC}  日志目录:      ${LOG_DIR}/"
echo -e "${CYAN}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "停止服务: ${YELLOW}bash $PROJECT_DIR/stop.sh${NC}"
echo ""

# ==============================
# 6. 进程守护 (可选)
# ==============================
if [ "${1:-}" = "--watch" ]; then
    log "进程守护模式已启用 (每10秒检查)..."
    while true; do
        sleep 10
        if ! kill -0 $(cat "$PID_DIR/backend.pid") 2>/dev/null; then
            warn "后端已挂，重启中..."
            cd "$BACKEND_DIR"
            PYTHONPATH="$BACKEND_DIR" python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 \
                > "$LOG_DIR/backend.log" 2>&1 &
            echo $! > "$PID_DIR/backend.pid"
        fi
        if ! kill -0 $(cat "$PID_DIR/static.pid") 2>/dev/null; then
            warn "静态服务已挂，重启中..."
            cd "$PROJECT_DIR"
            python3 serve.py \
                > "$LOG_DIR/static.log" 2>&1 &
            echo $! > "$PID_DIR/static.pid"
        fi
    done
fi
