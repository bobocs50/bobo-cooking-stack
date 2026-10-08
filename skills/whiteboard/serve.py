"""Local whiteboard server for the /whiteboard skill: serves board.html (Excalidraw)
with a Mermaid file converted in the browser, and writes the edited scene and a PNG
next to the .mmd.

Usage: python serve.py <path/to/slug.mmd> [--port 0] [--no-open]

Cost: free - local only
"""
import argparse
import base64
import json
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent


def make_handler(mmd, state):
    scene_path = mmd.with_suffix(".excalidraw")
    png_path = mmd.with_suffix(".png")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            print("%s %s" % (self.address_string(), fmt % args), flush=True)

        def _send(self, code, body=b"", ctype="text/plain; charset=utf-8"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Allow", "GET, POST, OPTIONS")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/":
                self._send(200, (HERE / "board.html").read_bytes(), "text/html; charset=utf-8")
            elif path == "/mermaid":
                self._send(200, mmd.read_bytes())
            elif path == "/scene":
                if scene_path.exists():
                    self._send(200, scene_path.read_bytes(), "application/json")
                else:
                    self._send(404, b"no saved scene")
            else:
                self._send(404, b"not found")

        def do_POST(self):
            path = self.path.split("?")[0]
            if path not in ("/save", "/done"):
                self._send(404, b"not found")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                data = json.loads(self.rfile.read(length))
                scene_path.write_text(data["scene"], encoding="utf-8")
                png_path.write_bytes(base64.b64decode(data["png_base64"]))
            except (ValueError, KeyError, OSError) as e:
                self._send(400, ("bad request: %s" % e).encode())
                return
            self._send(200, b'{"ok": true}', "application/json")
            if path == "/done":
                state["done"] = True
                print("wrote %s" % scene_path, flush=True)
                print("wrote %s" % png_path, flush=True)
                threading.Thread(target=self.server.shutdown, daemon=True).start()

    return Handler


def main():
    ap = argparse.ArgumentParser(description="Local Excalidraw whiteboard for a Mermaid file")
    ap.add_argument("mmd", help="path to the .mmd file")
    ap.add_argument("--port", type=int, default=0, help="port (0 = free port)")
    ap.add_argument("--no-open", action="store_true", help="do not open the browser")
    args = ap.parse_args()

    mmd = Path(args.mmd).resolve()
    if not mmd.is_file():
        print("error: Mermaid file not found: %s" % mmd, file=sys.stderr)
        return 2

    state = {"done": False}
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(mmd, state))
    url = "http://127.0.0.1:%d/" % server.server_address[1]
    print("whiteboard at %s" % url, flush=True)
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("interrupted before Done", file=sys.stderr)
        return 1
    finally:
        server.server_close()
    return 0 if state["done"] else 1


if __name__ == "__main__":
    sys.exit(main())
