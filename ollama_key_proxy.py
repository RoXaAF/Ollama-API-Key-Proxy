#!/usr/bin/env python3
"""Ollama API-key proxy + management UI. No dependencies (Python 3.8+).

Run:   ADMIN_PASSWORD=choose-one python3 ollama_key_proxy.py
Open:  http://localhost:8080
"""
import hashlib, http.client, json, os, secrets, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

OLLAMA = urlparse(os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"))
PORT = int(os.environ.get("PORT", "8080"))
HOST = os.environ.get("HOST", "127.0.0.1")  # use 0.0.0.0 to allow other machines
DB_FILE = os.environ.get("KEYS_FILE", "keys.json")
ADMIN = os.environ.get("ADMIN_PASSWORD") or secrets.token_urlsafe(12)
LOCK = threading.Lock()


def load():
    try:
        with open(DB_FILE) as f:
            return json.load(f)
    except Exception:
        return []


def save(keys):
    tmp = DB_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(keys, f, indent=2)
    os.replace(tmp, DB_FILE)


def h(k):
    return hashlib.sha256(k.encode()).hexdigest()


HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ollama API Keys</title>
<style>
:root{--bg:#f6f6f4;--card:#fff;--tx:#1d1d1b;--mu:#6b6b66;--bd:#e2e2dc;--ac:#c4622d;--ok:#2d7a4f}
@media(prefers-color-scheme:dark){:root{--bg:#171716;--card:#222220;--tx:#eeeeea;--mu:#9a9a92;--bd:#38382f;--ac:#e0824e;--ok:#5fbf8a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.5 system-ui,sans-serif}
main{max-width:760px;margin:0 auto;padding:32px 16px}
h1{font-size:22px;margin:0 0 4px}p.s{color:var(--mu);margin:0 0 24px}
.card{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:18px;margin-bottom:16px}
h2{font-size:15px;margin:0 0 12px}
input,select{width:100%;padding:9px 11px;border:1px solid var(--bd);border-radius:8px;background:var(--bg);color:var(--tx);font:inherit}
button{padding:9px 14px;border:0;border-radius:8px;background:var(--ac);color:#fff;font:inherit;cursor:pointer}
button.g{background:transparent;color:var(--mu);border:1px solid var(--bd)}button.d{background:transparent;color:#c0392b;border:1px solid var(--bd)}
.row{display:flex;gap:8px}code,pre{font:13px ui-monospace,monospace}
pre{background:var(--bg);border:1px solid var(--bd);border-radius:8px;padding:10px;overflow-x:auto;margin:8px 0 0}
.key{background:var(--bg);border:1px dashed var(--ok);border-radius:8px;padding:10px;word-break:break-all;margin:10px 0}
table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:8px 6px;border-bottom:1px solid var(--bd);font-size:13px}
th{color:var(--mu);font-weight:500}.mu{color:var(--mu);font-size:13px}.hide{display:none}
</style></head><body><main>
<h1>Ollama API Keys</h1><p class="s">Create keys for your agents and editors. Keys are shown once.</p>

<div class="card" id="login"><h2>Admin password</h2><div class="row">
<input id="pw" type="password" placeholder="ADMIN_PASSWORD" autofocus><button id="go">Unlock</button></div>
<p class="mu" id="err"></p></div>

<div id="app" class="hide">
<div class="card"><h2>Create a key</h2><div class="row">
<input id="name" placeholder="Name, e.g. zed-laptop"><button id="mk">Create key</button></div>
<div id="new" class="hide"><div class="key" id="kv"></div>
<div class="row"><button class="g" id="cp">Copy key</button></div>
<p class="mu">Connection settings for your tool:</p>
<div class="row"><select id="mdl"></select></div>
<pre id="snip"></pre></div></div>

<div class="card"><h2>Your keys</h2><table><thead><tr><th>Name</th><th>Key</th><th>Requests</th><th>Last used</th><th></th></tr></thead>
<tbody id="rows"></tbody></table><p class="mu hide" id="empty">No keys yet.</p></div>
</div>

<script>
const $=id=>document.getElementById(id);let PW=sessionStorage.getItem('pw')||'',KEY='';
const base=location.origin+'/v1';
async function api(p,o={}){const r=await fetch('/admin/'+p,{...o,headers:{'X-Admin-Password':PW,'Content-Type':'application/json'}});
 if(r.status==401)throw new Error('Wrong password');if(!r.ok)throw new Error(await r.text());return r.json()}
function snip(){const m=$('mdl').value||'MODEL';
 $('snip').textContent=`Base URL: ${base}\nAPI key:  ${KEY}\nModel:    ${m}\n\ncurl ${base}/chat/completions \\\n  -H "Authorization: Bearer ${KEY}" \\\n  -H "Content-Type: application/json" \\\n  -d '{"model":"${m}","messages":[{"role":"user","content":"hi"}]}'`}
async function refresh(){const ks=await api('keys');const t=$('rows');t.innerHTML='';
 $('empty').classList.toggle('hide',ks.length>0);
 for(const k of ks){const tr=document.createElement('tr');
  for(const v of [k.name,k.prefix+'…',k.requests,k.last_used?new Date(k.last_used*1000).toLocaleString():'never']){const td=document.createElement('td');td.textContent=v;tr.appendChild(td)}
  const td=document.createElement('td');const b=document.createElement('button');b.className='d';b.textContent='Revoke';
  b.onclick=async()=>{if(confirm('Revoke '+k.name+'?')){await api('keys/'+k.id,{method:'DELETE'});refresh()}};td.appendChild(b);tr.appendChild(td);t.appendChild(tr)}}
async function start(){try{await api('keys');$('login').classList.add('hide');$('app').classList.remove('hide');sessionStorage.setItem('pw',PW);
 try{const m=await api('models');for(const n of m){const o=document.createElement('option');o.textContent=n;$('mdl').appendChild(o)}}catch(e){}
 refresh()}catch(e){$('err').textContent=e.message}}
$('go').onclick=()=>{PW=$('pw').value;start()};$('pw').onkeydown=e=>{if(e.key=='Enter')$('go').click()};
$('mk').onclick=async()=>{const n=$('name').value.trim()||'unnamed';const r=await api('keys',{method:'POST',body:JSON.stringify({name:n})});
 KEY=r.key;$('kv').textContent=KEY;$('new').classList.remove('hide');$('name').value='';snip();refresh()};
$('cp').onclick=()=>{navigator.clipboard.writeText(KEY);$('cp').textContent='Copied'};
$('mdl').onchange=snip;if(PW)start();
</script></main></body></html>"""


class H(BaseHTTPRequestHandler):
    server_version = "OllamaKeyProxy"

    def log_message(self, *a):
        pass

    def log_request(self, code="-", size="-"):
        print("%s %s -> %s" % (self.command, self.path, code), flush=True)

    def send_json(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,DELETE,OPTIONS")

    def do_OPTIONS(self):
        self.send_response(204)
        self.cors()
        self.end_headers()

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def is_admin(self):
        return secrets.compare_digest(self.headers.get("X-Admin-Password", ""), ADMIN)

    def admin(self, method):
        if not self.is_admin():
            return self.send_json(401, {"error": "unauthorized"})
        p = self.path.split("?")[0]
        if p == "/admin/keys" and method == "GET":
            with LOCK:
                return self.send_json(200, [{k: v for k, v in x.items() if k != "hash"} for x in load()])
        if p == "/admin/keys" and method == "POST":
            name = (json.loads(self.body() or b"{}").get("name") or "unnamed")[:60]
            key = "sk-local-" + secrets.token_hex(24)
            with LOCK:
                keys = load()
                keys.append({"id": secrets.token_hex(4), "name": name, "hash": h(key), "prefix": key[:13],
                             "created": int(time.time()), "last_used": None, "requests": 0})
                save(keys)
            return self.send_json(200, {"key": key})
        if p.startswith("/admin/keys/") and method == "DELETE":
            kid = p.rsplit("/", 1)[1]
            with LOCK:
                save([k for k in load() if k["id"] != kid])
            return self.send_json(200, {"ok": True})
        if p == "/admin/models" and method == "GET":
            try:
                c = http.client.HTTPConnection(OLLAMA.hostname, OLLAMA.port or 11434, timeout=5)
                c.request("GET", "/api/tags")
                d = json.loads(c.getresponse().read())
                return self.send_json(200, [m["name"] for m in d.get("models", [])])
            except Exception:
                return self.send_json(200, [])
        self.send_json(404, {"error": "not found"})

    def authed(self):
        tok = self.headers.get("Authorization", "")
        tok = tok[7:] if tok.lower().startswith("bearer ") else self.headers.get("x-api-key", "")
        tok = tok.strip()
        if not tok:
            print("  auth failed: no key sent (check the key field in the client)", flush=True)
            return False
        digest = h(tok)
        with LOCK:
            keys = load()
            for k in keys:
                if secrets.compare_digest(k["hash"], digest):
                    k["requests"] += 1
                    k["last_used"] = int(time.time())
                    save(keys)
                    return True
        print("  auth failed: unknown/revoked key starting %s" % tok[:13], flush=True)
        return False

    def proxy(self, method):
        if not self.authed():
            self.send_response(401)
            self.cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            return self.wfile.write(b'{"error":{"message":"Invalid API key","type":"invalid_request_error"}}')
        data = self.body()
        hdrs = {k: v for k, v in self.headers.items()
                if k.lower() not in ("host", "authorization", "x-api-key", "content-length", "connection",
                                     "origin", "referer", "accept-encoding")}
        try:
            c = http.client.HTTPConnection(OLLAMA.hostname, OLLAMA.port or 11434, timeout=600)
            c.request(method, self.path, body=data or None, headers=hdrs)
            r = c.getresponse()
        except Exception as e:
            return self.send_json(502, {"error": "Ollama unreachable: %s" % e})
        self.send_response(r.status)
        for k, v in r.getheaders():
            if k.lower() not in ("transfer-encoding", "content-length", "connection") \
                    and not k.lower().startswith("access-control-"):
                self.send_header(k, v)
        self.cors()
        self.end_headers()
        try:
            while True:
                chunk = r.read1(8192)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            c.close()

    def route(self, method):
        p = self.path.split("?")[0]
        if p.startswith("/admin/"):
            return self.admin(method)
        if method == "GET" and p in ("/", "/index.html"):
            b = HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            return self.wfile.write(b)
        if p.startswith("/v1/") or p.startswith("/api/"):
            return self.proxy(method)
        self.send_json(404, {"error": "not found"})

    def do_GET(self): self.route("GET")
    def do_POST(self): self.route("POST")
    def do_DELETE(self): self.route("DELETE")


if __name__ == "__main__":
    if not os.environ.get("ADMIN_PASSWORD"):
        print("No ADMIN_PASSWORD set. Temporary admin password: %s" % ADMIN)
    print("UI:        http://%s:%d" % ("localhost" if HOST == "127.0.0.1" else HOST, PORT))
    print("Base URL:  http://localhost:%d/v1   ->  Ollama at %s" % (PORT, OLLAMA.geturl()))
    ThreadingHTTPServer((HOST, PORT), H).serve_forever()