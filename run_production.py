"""
Stranger Builds 2026 - Production Unified Gateway for Render Deployment.
Hosts the Full-Stack Web Portal on $PORT while proxying /api/* and /health
to the underlying Fetch.ai Autonomous Agent.
"""

import os
import sys
import time
import signal
import subprocess
import urllib.request
import urllib.error
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socketserver

# Determine ports: Render injects $PORT (usually 10000 or custom)
PUBLIC_PORT = int(os.getenv("PORT", "8000"))
INTERNAL_AGENT_PORT = 8001 if PUBLIC_PORT == 8000 else 8000

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")


class UnifiedProductionHandler(SimpleHTTPRequestHandler):
    """
    HTTP Request Handler that serves the responsive frontend for web users
    and routes /api/*, /health, and ACP queries to the Fetch.ai Agent.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200, "OK")
        self.end_headers()

    def do_GET(self):
        if self.path == "/health" or self.path.startswith("/api/"):
            self._proxy_to_agent("GET")
        elif self.path == "/agent-info":
            self.path = "/"
            self._proxy_to_agent("GET")
        elif self.path in ("/", "/index.html"):
            self.path = "/index.html"
            super().do_GET()
        else:
            # Check if file exists in frontend, otherwise fallback to index.html for SPA
            rel_path = self.path.lstrip("/").split("?")[0]
            if os.path.exists(os.path.join(FRONTEND_DIR, rel_path)):
                super().do_GET()
            else:
                self.path = "/index.html"
                super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/") or self.path in ("/submit", "/pay"):
            self._proxy_to_agent("POST")
        else:
            self.send_error(404, "Endpoint Not Found")

    def _proxy_to_agent(self, method: str):
        target_url = f"http://127.0.0.1:{INTERNAL_AGENT_PORT}{self.path}"
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        req = urllib.request.Request(target_url, data=body, method=method)
        for key, val in self.headers.items():
            if key.lower() not in ("host", "content-length"):
                req.add_header(key, val)

        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = resp.read()
                self.send_response(resp.status)
                for h_key, h_val in resp.headers.items():
                    if h_key.lower() not in ("access-control-allow-origin", "transfer-encoding"):
                        self.send_header(h_key, h_val)
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as exc:
            err_data = exc.read()
            self.send_response(exc.code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(err_data)
        except Exception as exc:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(f'{{"error": "Agent Gateway unreachable: {exc}"}}'.encode("utf-8"))


def start_production():
    print("=" * 65)
    print("STRANGER BUILDS 2026 - RENDER PRODUCTION SERVER LAUNCH")
    print(f"Public Web Gateway Port  : {PUBLIC_PORT}")
    print(f"Internal Agent Core Port : {INTERNAL_AGENT_PORT}")
    print(f"Frontend Static Root     : {FRONTEND_DIR}")
    print("=" * 65)

    # 1. Start the Fetch.ai primary agent in the background
    agent_env = os.environ.copy()
    agent_env["AGENT_PORT"] = str(INTERNAL_AGENT_PORT)
    agent_env["PYTHONUNBUFFERED"] = "1"

    agent_cmd = [sys.executable, os.path.join(BASE_DIR, "main.py")]
    print(f"Spawning Agent Core: {' '.join(agent_cmd)} (Port {INTERNAL_AGENT_PORT})...")
    agent_proc = subprocess.Popen(agent_cmd, env=agent_env)

    # Wait for the agent to initialize
    print("Awaiting agent readiness on /health...")
    ready = False
    for attempt in range(25):
        time.sleep(1.0)
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{INTERNAL_AGENT_PORT}/health", timeout=2) as r:
                if r.status == 200:
                    ready = True
                    print("✓ Agent Core is ONLINE and healthy!")
                    break
        except Exception:
            continue

    if not ready:
        print("⚠ Warning: Agent initialization took longer than expected; starting gateway anyway.")

    # 2. Start Unified Gateway Server on 0.0.0.0:PUBLIC_PORT
    socketserver.TCPServer.allow_reuse_address = True
    with HTTPServer(("0.0.0.0", PUBLIC_PORT), UnifiedProductionHandler) as httpd:
        print(f"✓ Production Gateway online at http://0.0.0.0:{PUBLIC_PORT}/")

        def handle_shutdown(signum, frame):
            print("\nShutting down production services...")
            httpd.server_close()
            agent_proc.terminate()
            sys.exit(0)

        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)

        try:
            httpd.serve_forever()
        except (KeyboardInterrupt, SystemExit):
            handle_shutdown(None, None)


if __name__ == "__main__":
    start_production()
