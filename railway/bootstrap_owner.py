"""Set Suparagent's owner passphrase from SUPARAGENT_OWNER_PASSPHRASE.

Upstream lets the owner set the passphrase only from the server itself (a loopback browser or
`python -m app.auth.cli set-passphrase`), so a fresh public server can't be claimed by whoever finds
it first. On Railway the template generates the passphrase instead, and this script applies it:

- on the first start, when no passphrase is set yet;
- again only when the variable's value changes (a SHA-256 of the last applied value is kept on the
  volume), so changing the variable and redeploying resets a forgotten passphrase, and a restart
  never overrides a passphrase you set later with the CLI.

Prints no secret. Exits 0 when there's nothing to do.
"""

import asyncio
import hashlib
import os
import sys
from pathlib import Path

sys.path.insert(0, os.environ.get("SUPARAGENT_BACKEND_DIR", "/app/backend"))

MARKER = Path(os.environ.get("RAILWAY_OWNER_MARKER", "/data/.railway-owner-passphrase.sha256"))


async def main() -> int:
    passphrase = os.environ.get("SUPARAGENT_OWNER_PASSPHRASE", "")
    from app.auth import credentials, people, store
    from app.db.session import AsyncSessionLocal, engine

    try:
        async with AsyncSessionLocal() as db:
            configured = await store.owner_configured(db)
            if not passphrase:
                if not configured:
                    print("SUPARAGENT_OWNER_PASSPHRASE is empty and no owner passphrase is set: nobody can sign "
                          "in until you set the variable (at least 10 characters) and redeploy.", file=sys.stderr)
                return 0
            digest = hashlib.sha256(passphrase.encode()).hexdigest()
            applied = MARKER.read_text().strip() if MARKER.exists() else ""
            if configured and applied == digest:
                return 0
            if configured and not applied:
                # A passphrase set some other way (the CLI) before this script ever ran: leave it.
                MARKER.write_text(digest + "\n")
                print("Owner passphrase already set; SUPARAGENT_OWNER_PASSPHRASE recorded, not applied.")
                return 0
            try:
                await store.set_passphrase(db, passphrase, first_time_only=False)
            except credentials.WeakPassphrase as exc:
                print(f"SUPARAGENT_OWNER_PASSPHRASE was not applied: {exc}", file=sys.stderr)
                return 0
            await people.ensure_owner_person(db)
            MARKER.write_text(digest + "\n")
            print("Owner passphrase " + ("replaced" if configured else "set") + " from SUPARAGENT_OWNER_PASSPHRASE.")
            return 0
    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
