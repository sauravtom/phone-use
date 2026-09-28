# Hosted phone-use MCP

Cloudflare Worker + Durable Objects + OAuth KV. No model provider, user account,
or API key is needed. The official Cloudflare OAuth provider handles OAuth tokens,
S256 PKCE and browser-bound consent. Each one-time pairing code authorizes one
explicit ADB device through the Python bridge's outbound WebSocket.

`https://phone-use.xagi.in/mcp` is the production resource. `/` has connection
instructions, `/privacy` explains data handling, and `/terms` describes service use.

## Develop on a server

```sh
npm ci
npm run check
npx wrangler dev
```

For loopback integration tests, make a separate ignored config under `.wrangler/`
with `main: "../src/index.ts"`, no routes, and
`vars.PUBLIC_ORIGIN: "http://127.0.0.1:8787"`; copy the bindings and migration from
`wrangler.jsonc`. Run `wrangler dev --config .wrangler/local.jsonc --port 8787`, then
run `uv run python scripts/relay-smoke.py` from the repository root. All development
and tests for this project are performed on the AWS host.

The integration test uses a fake ADB subprocess, not a physical phone. The opt-in
`uv run python scripts/remote-device-smoke.py --serial SERIAL` runs the real CLI
bridge and existing fixture workflow through the production HTTPS endpoint; use
only a disposable, explicitly authorized emulator with the fixture APK installed.

## Deploy

Authenticate with `wrangler whoami`. Create an OAuth KV namespace and put its ID
in `wrangler.jsonc`. Configure a custom domain in your own Cloudflare zone and set
PUBLIC_ORIGIN to exactly that HTTPS origin. `npm run deploy` provisions the Worker
and Durable Object migration. The checked-in config names this project's domain.

Set `DOMAIN_CHALLENGE` with `wrangler secret put DOMAIN_CHALLENGE` to the exact
OpenAI domain verification token. It is served only at
`/.well-known/openai-apps-challenge`. This challenge is public verification material,
not an API credential.

Pairing codes live for 10 minutes. Phone sessions and refresh grants live for at
most 8 hours; access tokens live for 1 hour. Stop the bridge to terminate access.
A lost bridge cannot execute commands; a clean shutdown also deletes its session.
The server stores no screen or command payloads in its application storage and
Workers observability is disabled. Cloudflare platform security logs and storage
backups are subject to Cloudflare retention. OAuth client records expire in 30 days.

The MCP handler serves checked-in tool schemas generated from `create_server()`.
Keep them aligned when changing Python tool definitions. Do not weaken OAuth,
per-device serial checks, one-time pairing, CSRF/PKCE checks or command deadlines.
A timeout never triggers automatic input retry: the phone may have received it.
