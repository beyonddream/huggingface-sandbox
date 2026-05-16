<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/banner-dark.png">
  <img alt="huggingface-sandbox" src="assets/banner-light.png">
</picture>

Modal-style sandbox API on top of Hugging Face Jobs.

```python
from huggingface_sandbox import Sandbox

sb = Sandbox.create(image="python:3.12")
proc = sb.exec("python", "-c", "print(1+1)")  # → CompletedProcess(stdout='2\n', returncode=0, ...)
sb.write_file("/tmp/foo.txt", "hello")
print(sb.read_file("/tmp/foo.txt"))           # → 'hello'
sb.terminate()
```

Cloudflare Tunnel is the default. To use ngrok instead, pass `tunnel="ngrok"` and provide an ngrok auth token:

```python
sb = Sandbox.create(
    image="python:3.12",
    tunnel="ngrok",
    ngrok_authtoken="your-ngrok-token",
)
```

You can also set `NGROK_AUTHTOKEN` in the local environment instead of passing `ngrok_authtoken`.

## How it works

`Sandbox.create()` launches an HF Job that:

1. `pip install`s a tiny FastAPI RPC server (FastAPI + uvicorn)
2. starts the server on `localhost:8000`
3. opens either a free [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) or an [ngrok](https://ngrok.com/) tunnel so the master process can reach it

The client polls the job logs for the tunnel URL, then talks to the sandbox over plain HTTPS.

`exec`, `write_file`, `read_file` are simple authenticated POSTs.
`terminate()` cancels the job.

## Install

```bash
pip install huggingface-sandbox
```

Requires `hf auth login` (the same token is forwarded to the sandbox so it can access HF Hub).

## Limits

- Image must have Python + `pip` (used to install the RPC server and download `cloudflared` or `ngrok`).
- Cloudflare's free `trycloudflare.com` URLs are best-effort — fine for benchmarks, not production.
- ngrok requires an auth token. Pass `ngrok_authtoken` or set `NGROK_AUTHTOKEN` before calling `Sandbox.create(..., tunnel="ngrok")`.

## Security

The sandbox runs **untrusted code by design**. A few things to be aware of:

- **HF token forwarding is opt-in.** By default, your HF token is *not* exposed to the sandbox. Pass `forward_hf_token=True` to `Sandbox.create()` if your workload needs it. With it enabled, anything running inside the sandbox can read the token from `/proc/self/environ` and use it to act as you on the Hub.
- **The tunnel provider sees all tunnel traffic.** Requests, responses, and the auth token transit Cloudflare's infrastructure (via `trycloudflare.com`) or ngrok's infrastructure. Don't run sensitive workloads through it.
- **Auth token** is a 256-bit random URL-safe string per sandbox, sent as `Bearer` on every authenticated endpoint. The tunnel URL alone gets you nothing.

## Telemetry

`huggingface-sandbox` reports anonymous usage data to help us understand how the library is used. Two events are sent per sandbox:

- `huggingface-sandbox/create` — flavor, timeout, tunnel provider, whether `forward_hf_token` was set, and a random per-sandbox session id
- `huggingface-sandbox/terminate` — same session id, duration in seconds, and termination reason

We never send: the image name, commands, file paths, file contents, the tunnel URL, the auth token, your HF token, your username, or anything from inside the sandbox.

Disable by setting `HF_HUB_DISABLE_TELEMETRY=1` (or `DO_NOT_TRACK=1`).
