#!/usr/bin/env python3
import http.server, json, os, urllib.request, urllib.error

PORT = int(os.environ.get("PORT", 8765))

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200); self.cors(); self.end_headers()

    def do_GET(self):
        p = self.path.split("?")[0]
        if p in ("/", "/index.html"):
            self.serve("index.html", "text/html; charset=utf-8")
        elif p == "/api/status":
            k = get_key()
            self.json({"ok": True, "hasKey": bool(k)})
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.path == "/api/key":
            d = json.loads(body)
            k = d.get("key", "").strip()
            if not k.startswith("sk-"):
                self.json({"error": "Key must start with sk-"}, 400); return
            # On cloud: save to environment isn't persistent, use a file
            with open("api_key.txt", "w") as f: f.write(k)
            self.json({"ok": True})
        elif self.path == "/api/claude":
            k = get_key()
            if not k:
                self.json({"error": "No API key saved."}, 401); return
            try:
                req = urllib.request.Request(
                    "https://api.anthropic.com/v1/messages",
                    data=body,
                    headers={
                        "Content-Type": "application/json",
                        "x-api-key": k,
                        "anthropic-version": "2023-06-01"
                    },
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=60) as r:
                    result = r.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.cors(); self.end_headers()
                self.wfile.write(result)
            except urllib.error.HTTPError as e:
                err = e.read()
                self.send_response(e.code)
                self.send_header("Content-Type", "application/json")
                self.cors(); self.end_headers()
                self.wfile.write(err)
            except Exception as e:
                self.json({"error": str(e)}, 500)
        else:
            self.send_response(404); self.end_headers()

    def serve(self, filename, ctype):
        try:
            with open(filename, "rb") as f: data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", len(data))
            self.end_headers(); self.wfile.write(data)
        except FileNotFoundError:
            self.send_response(404); self.end_headers()

    def json(self, data, status=200):
        b = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.cors()
        self.send_header("Content-Length", len(b))
        self.end_headers(); self.wfile.write(b)

def get_key():
    # Check file first, then environment variable
    if os.path.exists("api_key.txt"):
        return open("api_key.txt").read().strip()
    return os.environ.get("ANTHROPIC_API_KEY", "")

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print(f"Server running on port {PORT}")
    http.server.HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
