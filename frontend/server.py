"""
Frontend Static Server for Stranger Builds 2026.
Serves the responsive Web UI on port 3000 with CORS and clean routing.
"""

import http.server
import socketserver
import os
from functools import partial

PORT = 3000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))


class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.end_headers()


def run():
    handler = partial(CORSHTTPRequestHandler, directory=DIRECTORY)
    # Enable address reuse
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), handler) as httpd:
        print(f"Frontend Web Portal running at http://localhost:{PORT}/")
        print(f"Serving files from {DIRECTORY}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down frontend server.")
            httpd.server_close()


if __name__ == "__main__":
    run()
