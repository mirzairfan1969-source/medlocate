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
            if len(k) < 20:
                self.json({"error": "Invalid key"}, 400); return
            with open("api_key.txt", "w") as f: f.write(k)
            self.json({"ok": True})

        elif self.path == "/api/analyze":
            # Receive: { "image_b64": "...", "prompt": "..." }
            k = get_key()
            if not k:
                self.json({"error": "No API key saved."}, 401); return
            try:
                d = json.loads(body)
                b64  = d["image_b64"]
                prompt = d["prompt"]

                # Build Gemini request
                gemini_body = json.dumps({
                    "contents": [{
                        "parts": [
                            {"inline_data": {"mime_type": "image/jpeg", "data": b64}},
                            {"text": prompt}
                        ]
                    }],
                    "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048}
                }).encode()

                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={k}"
                req = urllib.request.Request(url, data=gemini_body, headers={"Content-Type": "application/json"}, method="POST")
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

        elif self.path == "/api/search":
            # Text-only search: { "prompt": "..." }
            k = get_key()
            if not k:
                self.json({"error": "No API key saved."}, 401); return
            try:
                d = json.loads(body)
                prompt = d["prompt"]

                gemini_body = json.dumps({
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.1, "maxOutputTokens": 400}
                }).encode()

                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={k}"
                req = urllib.request.Request(url, data=gemini_body, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=30) as r:
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
    if os.path.exists("api_key.txt"):
        return open("api_key.txt").read().strip()
    return os.environ.get("GEMINI_API_KEY", "")

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print(f"MedLocate running on port {PORT}")
    http.server.HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
