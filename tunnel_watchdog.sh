#!/bin/bash
# Tunnel watchdog — serveo.net with fixed subdomain
# URL: https://autostamp.serveo.net (stable, won't change)
LOG="/home/udg/automaticstamping/logs/tunnel.log"
URL_FILE="/home/udg/automaticstamping/.public_url"
FIXED_URL="https://autostamp.serveo.net"
mkdir -p "$(dirname "$LOG")"

echo "=== Tunnel Watchdog (serveo.net) ==="
echo "Fixed URL: $FIXED_URL"
echo "$FIXED_URL" > "$URL_FILE"

while true; do
    echo "[$(date +%H:%M:%S)] Connecting to serveo.net..."
    
    ssh -o StrictHostKeyChecking=no \
        -o ServerAliveInterval=10 \
        -o ServerAliveCountMax=3 \
        -o ExitOnForwardFailure=yes \
        -o ConnectTimeout=10 \
        -R autostamp:80:localhost:5173 \
        serveo.net 2>&1 | while IFS= read -r line; do
        echo "[$(date +%H:%M:%S)] $line" >> "$LOG"
    done
    
    echo "[$(date +%H:%M:%S)] Disconnected, reconnect in 5s..."
    sleep 5
done
