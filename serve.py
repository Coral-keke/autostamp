#!/usr/bin/env python3
"""Static file server + API reverse proxy for production."""
import http.server
import urllib.request
import urllib.error
import os
import sys

DIST_DIR = sys.argv[1] if len(sys.argv) > 1 else "/home/udg/automaticstamping/frontend/dist"
API_TARGET = "http://localhost:8000"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 5173


class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIST_DIR, **kwargs)

    def do_GET(self):
        if self.path.startswith("/api/"):
            self._proxy()
        else:
            self._serve_spa()

    def do_POST(self):
        if self.path.startswith("/api/"):
            self._proxy()
        else:
            self.send_error(404)

    def do_PUT(self):
        if self.path.startswith("/api/"):
            self._proxy()
        else:
            self.send_error(404)

    def do_PATCH(self):
        if self.path.startswith("/api/"):
            self._proxy()
        else:
            self.send_error(404)

    def do_DELETE(self):
        if self.path.startswith("/api/"):
            self._proxy()
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,PATCH,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def _proxy(self):
        url = f"{API_TARGET}{self.path}"
        body = None
        if self.command in ("POST", "PUT", "PATCH"):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else None

        req = urllib.request.Request(
            url, data=body, method=self.command
        )
        for k, v in self.headers.items():
            if k.lower() not in ("host", "connection"):
                req.add_header(k, v)

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    if k.lower() not in ("transfer-encoding", "connection"):
                        self.send_header(k, v)
                self.end_headers()
                self.wfile.write(resp.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.end_headers()
            self.wfile.write(e.read() or b"")
        except Exception as e:
            self.send_error(502, f"Upstream error: {e}")

    def _serve_spa(self):
        """Serve static file, falling back to index.html for SPA routing."""
        clean_path = self.path.split("?")[0].split("#")[0]
        file_path = os.path.join(DIST_DIR, clean_path.lstrip("/"))

        if os.path.isfile(file_path):
            return super().do_GET()

        # SPA fallback
        self.path = "/index.html"
        return super().do_GET()

    def log_message(self, fmt, *args):
        print(f"[static-proxy] {args[0]}", flush=True)


if __name__ == "__main__":
    server = http.server.HTTPServer(("0.0.0.0", PORT), ProxyHandler)
    print(f"Serving {DIST_DIR} on :{PORT} | API → {API_TARGET}", flush=True)
    server.serve_forever()
