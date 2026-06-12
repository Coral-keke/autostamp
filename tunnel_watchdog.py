#!/usr/bin/env python3
"""
Persistent SSH tunnel to localhost.run.
- Auto-reconnects with exponential backoff
- Extracts and saves the public URL
- Also serves a tiny status page at :9999
"""
import subprocess, time, re, os, sys, json, threading, http.server

LOCAL_PORT = 5173
REMOTE_PORT = 80
PUBLIC_URL_FILE = "/home/udg/automaticstamping/.public_url"
CURRENT_URL = None
URL_LOCK = threading.Lock()

# ── Tiny status HTTP server ──────────────────────────
class StatusHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"url": CURRENT_URL, "alive": CURRENT_URL is not None})
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body.encode())
    def log_message(self, *a): pass

def start_status_server():
    srv = http.server.HTTPServer(("127.0.0.1", 9999), StatusHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

# ── SSH tunnel with URL extraction ───────────────────
def run_tunnel():
    global CURRENT_URL
    cmd = [
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-o", "ServerAliveInterval=10",
        "-o", "ServerAliveCountMax=3",
        "-o", "ExitOnForwardFailure=yes",
        "-o", "ConnectTimeout=10",
        "-R", f"{REMOTE_PORT}:localhost:{LOCAL_PORT}",
        "nokey@localhost.run"
    ]
    
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, bufsize=1)
    
    # Match both "xxx.lhr.life" and "https://xxx.lhr.life"
    url_re = re.compile(r'(https?://)?([a-z0-9]+\.lhr\.life)')
    
    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        
        # Check for URL
        m = url_re.search(line)
        if m:
            url = "https://" + m.group(2)
            with URL_LOCK:
                if url != CURRENT_URL:
                    CURRENT_URL = url
                    with open(PUBLIC_URL_FILE, 'w') as f:
                        f.write(url)
                    print(f"\n{'='*60}")
                    print(f"  🌐 PUBLIC: {url}")
                    print(f"{'='*60}\n", flush=True)
    
    proc.wait()
    with URL_LOCK:
        CURRENT_URL = None

# ── Main loop ────────────────────────────────────────
def main():
    start_status_server()
    print("=== Tunnel Watchdog v2 ===", flush=True)
    print(f"Status page: http://localhost:9999", flush=True)
    
    failures = 0
    while True:
        try:
            print(f"[{time.strftime('%H:%M:%S')}] Connecting SSH tunnel...", flush=True)
            run_tunnel()
            failures = 0
            print(f"[{time.strftime('%H:%M:%S')}] Tunnel disconnected.", flush=True)
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] Error: {e}", flush=True)
        
        failures += 1
        wait = min(2 ** failures, 30)
        print(f"[{time.strftime('%H:%M:%S')}] Reconnect in {wait}s...", flush=True)
        time.sleep(wait)

if __name__ == "__main__":
    main()
