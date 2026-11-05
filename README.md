# Ollama API Key Proxy

A lightweight, dependency-free API-key proxy and web dashboard for local [Ollama](https://ollama.com/) models.

The proxy sits between your tools (AI agents, editors, and API clients) and your local Ollama server. It lets you create separate API keys, authenticate requests, monitor basic usage, and revoke keys without exposing Ollama directly to every client.

> **Status:** Small, self-hosted utility. Review the security notes before exposing it beyond your own machine or trusted network.

## Features

- **API key management:** Create named keys for different tools or users.
- **One-time key display:** A newly generated key is shown once. Copy and store it securely.
- **Hashed key storage:** Only SHA-256 hashes of API keys are stored in `keys.json`.
- **Authentication:** Accepts `Authorization: Bearer <key>` or the `X-API-Key` header.
- **Usage tracking:** Records request counts and the last-used timestamp for each key.
- **Revocation:** Delete a key from the dashboard to invalidate it.
- **Model discovery:** Reads available model names from Ollama's `/api/tags` endpoint.
- **Streaming passthrough:** Relays Ollama responses in chunks, including streamed responses.
- **Simple web UI:** Manage keys from your browser.
- **No third-party Python packages:** Uses the Python standard library.

## Screenshots

### API key management dashboard

Create and revoke keys, view request counts, and copy the connection details generated for a selected model.

![Ollama API key dashboard](assets/ollama-api-key-dashboard.png)

### Connect a model provider

Example provider configuration using the local proxy URL and a generated key.

![Model provider configuration](assets/model-provider-configuration.png)

> **Client configuration note:** This proxy forwards Ollama's OpenAI-compatible `/v1/` routes, including `/v1/chat/completions`. In clients that offer an API format selector, choose **OpenAI-compatible / Chat Completions**, not Anthropic Messages (`/v1/messages`), unless you separately add support for that protocol.

## Requirements

- Python **3.8 or newer**
- [Ollama](https://ollama.com/) installed and running
- At least one model pulled into Ollama

Check that Ollama is available:

```bash
ollama list
```

If you need a model, for example:

```bash
ollama pull gemma4:12b
```

Use a model name that actually appears in your `ollama list` output.

## Quick start

1. Save `ollama_key_proxy.py` to a directory.
2. Start Ollama.
3. Set an admin password and run the proxy.

### Linux / macOS

```bash
export ADMIN_PASSWORD="replace-this-with-a-long-random-password"
python3 ollama_key_proxy.py
```

### Windows PowerShell

```powershell
$env:ADMIN_PASSWORD = "replace-this-with-a-long-random-password"
python .\ollama_key_proxy.py
```

Open the dashboard:

```text
http://localhost:8080
```

Sign in with the `ADMIN_PASSWORD` value you configured.

If you do not set `ADMIN_PASSWORD`, the application generates a temporary password and prints it in the terminal at startup. Set your own password for predictable administration.

## Configuration

The application is configured through environment variables:

| Variable | Default | Description |
|---|---|---|
| `ADMIN_PASSWORD` | Random temporary password | Password required for dashboard administration and `/admin/` API requests. |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama server address. |
| `HOST` | `127.0.0.1` | Interface to bind to. Keep the default for local-only access. |
| `PORT` | `8080` | Port used by the proxy and dashboard. |
| `KEYS_FILE` | `keys.json` | File used to persist API key metadata and hashes. |

Example with a custom port and key database:

```bash
ADMIN_PASSWORD="use-a-strong-password" \
OLLAMA_URL="http://127.0.0.1:11434" \
HOST="127.0.0.1" \
PORT="8080" \
KEYS_FILE="./data/keys.json" \
python3 ollama_key_proxy.py
```

The parent directory for a custom `KEYS_FILE` must already exist and be writable.

## Create an API key

1. Open `http://localhost:8080`.
2. Enter the admin password.
3. Enter a descriptive name, such as `zed-laptop`, `my-agent`, or `local-editor`.
4. Select **Create key**.
5. Copy the generated key and save it in your tool's secret/API-key settings.

Keys use the `sk-local-` prefix. The full key is displayed only when it is created; the dashboard later displays only its prefix.

## Connect an API client

Use the proxy's base URL:

```text
http://localhost:8080/v1
```

Configure your client with:

| Setting | Value |
|---|---|
| Base URL | `http://localhost:8080/v1` |
| API key | Your generated `sk-local-...` key |
| API format | OpenAI-compatible Chat Completions |
| Model | A model installed in your Ollama instance, e.g. `gemma4:12b` |

### Test with curl

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer sk-local-YOUR_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma4:12b",
    "messages": [
      {"role": "user", "content": "Hello! Introduce yourself briefly."}
    ],
    "stream": false
  }'
```

Replace the example key and model with your own values.

You can also authenticate using `X-API-Key`:

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "X-API-Key: sk-local-YOUR_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{"model":"gemma4:12b","messages":[{"role":"user","content":"Hello"}]}'
```

## Endpoints

### Admin endpoints

These endpoints require the `X-Admin-Password` header.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/admin/keys` | List keys and usage metadata. Key hashes are not returned. |
| `POST` | `/admin/keys` | Create a key. JSON body: `{"name":"my-agent"}`. |
| `DELETE` | `/admin/keys/{id}` | Revoke a key by its ID. |
| `GET` | `/admin/models` | List model names reported by Ollama. |

Example:

```bash
curl http://localhost:8080/admin/keys \
  -H "X-Admin-Password: YOUR_ADMIN_PASSWORD"
```

### Proxied endpoints

Requests whose paths begin with `/v1/` or `/api/` are authenticated and forwarded to the configured Ollama server.

For example:

- `POST /v1/chat/completions`
- `GET /api/tags`

The proxy forwards the request path and body to Ollama. The exact endpoints available depend on the Ollama version and API compatibility.

## Data storage

The default `keys.json` file contains each key's:

- Internal ID
- Display name
- SHA-256 key hash
- Short key prefix
- Creation timestamp
- Last-used timestamp
- Request count

The full API key is not stored. Back up `keys.json` if you need to preserve the existing keys. Protect this file because it contains credential metadata and is required to validate keys.

## Security considerations

This project is intended as a simple local proxy, not a hardened public API gateway.

- **Keep it local by default.** The default `HOST=127.0.0.1` prevents other machines from connecting directly.
- **Use a strong admin password.** Anyone who can access the admin endpoints and knows this password can create or revoke keys.
- **Do not expose it directly to the public internet.** The current implementation does not provide TLS, rate limiting, per-key model restrictions, or brute-force protection.
- **Review the CORS policy.** The proxy currently allows all origins (`Access-Control-Allow-Origin: *`). Restrict this before using it in a browser-facing or public deployment.
- **Protect the network path.** The proxy uses plain HTTP connections. If traffic crosses an untrusted network, put it behind a properly configured HTTPS reverse proxy or VPN.
- **Protect the key database and backups.** Keep `keys.json` out of public repositories and restrict filesystem permissions.
- **Keep secrets out of Git.** Never commit real API keys, admin passwords, or a populated `keys.json` file.

If you bind to `0.0.0.0` to allow LAN access, understand that the service becomes reachable through the machine's network interfaces. Use a trusted network and additional access controls.

## Limitations

- Designed for a single local Ollama server.
- Key metadata is stored in a local JSON file, not a database.
- No user accounts or role-based access control.
- No per-key quotas, rate limits, or model permissions.
- No built-in TLS.
- The proxy does not translate Anthropic Messages requests into OpenAI Chat Completions requests.
- The configured Ollama connection is made using Python's `HTTPConnection`; use an HTTP Ollama URL.

## Troubleshooting

**The dashboard does not open**

- Confirm the Python process is still running.
- Check the startup output for the configured host and port.
- Make sure another process is not already using port `8080`.

**The API returns `401 Invalid API key`**

- Check that you copied the complete key when it was created.
- Confirm the client sends `Authorization: Bearer YOUR_KEY` or `X-API-Key: YOUR_KEY`.
- Check that the key has not been revoked.
- Confirm the proxy is using the same `KEYS_FILE` where the key was created.

**The proxy returns `502 Ollama unreachable`**

- Confirm Ollama is running.
- Check that `OLLAMA_URL` points to the correct host and port.
- Test Ollama directly, for example with `ollama list`.

**No models appear in the dashboard**

- Pull a model into Ollama.
- Confirm the Ollama server is reachable at `OLLAMA_URL`.
- Check the terminal output for connection errors.

## Project structure

```text
ollama-key-proxy/
├── ollama_key_proxy.py
├── README.md
└── assets/
    ├── model-provider-configuration.png
    └── ollama-api-key-dashboard.png
```

## License

No license is specified in this repository yet. Add a `LICENSE` file before presenting the project as open source, and choose a license that matches how you want others to use, modify, and distribute it.
