"""Simple local web server for report preview."""
from __future__ import annotations

import http.server
import json
import threading
import webbrowser
from pathlib import Path

STATIC_DIR = Path(__file__).parent / "static"


class PreviewHandler(http.server.BaseHTTPRequestHandler):
    """Serve preview page and report data."""

    report_content: str = ""
    feishu_content: str = ""
    dingtalk_content: str = ""

    def do_GET(self):
        if self.path == "/":
            self._serve_file(STATIC_DIR / "preview.html", "text/html")
        elif self.path == "/api/report":
            self._serve_json({
                "markdown": self.report_content,
                "feishu": self.feishu_content,
                "dingtalk": self.dingtalk_content,
            })
        else:
            self.send_error(404)

    def _serve_file(self, path: Path, content_type: str):
        if not path.exists():
            self.send_error(404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_json(self, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        pass  # Suppress request logs


def start_preview(
    report: str,
    feishu: str = "",
    dingtalk: str = "",
    port: int = 8686,
) -> None:
    """Start preview server and open browser."""
    PreviewHandler.report_content = report
    PreviewHandler.feishu_content = feishu
    PreviewHandler.dingtalk_content = dingtalk

    server = http.server.HTTPServer(("127.0.0.1", port), PreviewHandler)
    url = f"http://127.0.0.1:{port}"

    # Open browser in background
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    print(f"Preview server running at {url}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        print("\nServer stopped.")
