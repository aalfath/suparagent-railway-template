# Suparagent on Railway

A one-click [Railway](https://railway.com) template for [Suparagent](https://github.com/Anil-matcha/suparagent), the open-source, self-hosted workspace for AI coworkers: named agents with instructions, memory, routines, connected apps and your approval before they act.

## What it deploys

One service, built from this repo's `Dockerfile`:

- the official server image `ghcr.io/anil-matcha/suparagent:v0.8.7`, pinned by digest (`sha256:76081103077a8da4637d7c30e97ed72420f0c7322e2fab920472406f7848f79a`);
- the Claude Code (`@anthropic-ai/claude-code@2.1.328`) and Codex (`@openai/codex@0.170.0`) CLIs, installed the way upstream's `ENGINES` build argument does, so you can sign in to either from **Settings → Engines**. Gemini, Cursor, OpenRouter and any OpenAI-compatible endpoint work with an API key and need no CLI;
- a small start script (`railway/start.sh`) and `railway/bootstrap_owner.py`, which sets the owner passphrase from a generated variable.

Everything Suparagent keeps (the SQLite database, attachments, decision log, agent workspaces and the engines' sign-ins) is on a Railway volume at `/data`. The health check is `GET /api/v1/health`.

Upstream marks its releases as pre-releases and says the project is in active development; read its [known limitations](https://github.com/Anil-matcha/suparagent#known-limitations).

## Variables

| Variable | Default | What it is |
|---|---|---|
| `SUPARAGENT_OWNER_PASSPHRASE` | generated, 32 characters | The owner's sign-in passphrase. Find it in the service's **Variables** tab. Change it and redeploy to reset a forgotten passphrase. |
| `TOKEN_ENCRYPTION_KEYS` | generated Fernet key | Encrypts the credentials Suparagent stores. Keep a copy: losing or changing it makes saved keys unreadable, and backups don't contain it. |
| `SUPARAGENT_PUBLIC_URL` | `https://${{RAILWAY_PUBLIC_DOMAIN}}` | The address people use. Change it if you add a custom domain. |
| `PORT` | `8080` | The port the server listens on. |

The start script also sets, unless you override them: `TRUSTED_PROXIES=100.64.0.0/10` (Railway's edge proxy, so the sign-in cookie is marked `Secure`), `TRUSTED_HOSTS` (adds Railway's health checker), `LOCAL_EXECUTION_ENABLED=true` (agents can run; tools stay off until `LOCAL_TOOLS_ENABLED=true`, and every command still asks for approval) and `LOOPBACK_TRUST=off`.

### First sign-in

Open the public URL, choose **Sign in** and enter `SUPARAGENT_OWNER_PASSPHRASE`. Then connect an engine in **Settings → Engines**: save an OpenRouter or OpenAI-compatible key, or use **Sign in to Claude** / **Sign in to Codex** for the bundled CLIs. Invite teammates from **Settings → Account & privacy → People**.

Upstream normally lets the owner set the passphrase only from the server itself, so a fresh public server can't be claimed by whoever finds it first. This template generates it instead, and applies it on the first start. It applies it again only when you change the variable, so a passphrase you later set with `python -m app.auth.cli set-passphrase` survives restarts.

## Updates

Railway tells everyone who deployed this template when this repo's `main` branch changes, and you choose when to apply it. Each change bumps the pinned image digest or CLI versions and gets an entry in [CHANGELOG.md](CHANGELOG.md), with breaking changes first. Suparagent migrates its database on start and copies the SQLite file aside before a migration. GHCR keeps old tags of this image today, but if a pinned digest ever stops resolving, the next update here fixes the pin.

## Files

- `Dockerfile`: the pinned base image, the engine CLIs and the start command.
- `railway/start.sh`: Railway defaults, volume ownership, migration, owner passphrase, then the server.
- `railway/bootstrap_owner.py`: sets the owner passphrase from `SUPARAGENT_OWNER_PASSPHRASE`.

Suparagent is © its authors, Apache-2.0. This wrapper is maintained by Heron Technology.
