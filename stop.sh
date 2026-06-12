#!/bin/bash
# ============================================================
# 自动盖章系统 — 一键停止脚本
# ============================================================
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_DIR="$PROJECT_DIR/.pids"

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

stop_service() {
    local name=$1 pid_file="$PID_DIR/$2"
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if kill "$pid" 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} $name (pid=$pid) 已停止"
        else
            echo -e "  ${RED}✗${NC} $name 不在运行"
        fi
        rm -f "$pid_file"
    fi
}

echo "停止自动盖章系统..."

stop_service "SSH 隧道"      "tunnel.pid"
stop_service "静态服务"      "static.pid"
stop_service "FastAPI 后端"  "backend.pid"

# 强制杀端口残留
fuser -k 5173/tcp 2>/dev/null && echo "  清理端口 5173"
fuser -k 8000/tcp 2>/dev/null && echo "  清理端口 8000"

echo "全部停止 ✅"
