#!/bin/sh
# Start Suparagent on Railway. Fixed settings live here, so the template needs only a few variables.
set -eu

# Railway's volume is mounted root-owned: hand it to the image's user, then continue as that user.
if [ "$(id -u)" = "0" ]; then
  mkdir -p /data
  chown suparagent:suparagent /data
  exec setpriv --reuid=10001 --regid=10001 --init-groups -- "$0" "$@"
fi

# Listen on Railway's PORT on every IPv4 address (the image already sets SUPARAGENT_ALLOW_PUBLIC_BIND=1).
# IPv4 on purpose: on a dual-stack socket the edge proxy would show up as ::ffff:100.64.x.x and not
# match TRUSTED_PROXIES below.
export SUPARAGENT_HOST="${SUPARAGENT_HOST:-0.0.0.0}"
export SUPARAGENT_PORT="${PORT:-${SUPARAGENT_PORT:-8000}}"

# Railway's edge proxy reaches the container from 100.64.0.0/10. Believe its X-Forwarded-Proto and
# X-Forwarded-For from that range only, so the sign-in cookie is marked Secure.
export TRUSTED_PROXIES="${TRUSTED_PROXIES:-100.64.0.0/10}"
# Railway's health checker calls with Host: healthcheck.railway.app. The public name comes from
# SUPARAGENT_PUBLIC_URL and is trusted automatically.
export TRUSTED_HOSTS="${TRUSTED_HOSTS:-localhost,127.0.0.1,[::1],healthcheck.railway.app}"

# Agents run only when this is true (upstream's own example sets it). Tools (file edits, commands)
# stay off until LOCAL_TOOLS_ENABLED=true, and every command still asks for approval in the app.
export LOCAL_EXECUTION_ENABLED="${LOCAL_EXECUTION_ENABLED:-true}"
export LOOPBACK_TRUST="${LOOPBACK_TRUST:-off}"

if [ -z "${TOKEN_ENCRYPTION_KEYS:-}" ]; then
  echo "TOKEN_ENCRYPTION_KEYS is empty. Set it to a Fernet key (the template generates one)." >&2
  exit 1
fi
# The template generates a Fernet key. If the variable holds anything else (a hand-typed value), derive
# a Fernet key from it, the same way on every start, instead of failing on every request.
TOKEN_ENCRYPTION_KEYS="$(python - <<'PY'
import base64, hashlib, os, sys
from cryptography.fernet import Fernet
out = []
for key in (k.strip() for k in os.environ["TOKEN_ENCRYPTION_KEYS"].split(",")):
    if not key:
        continue
    try:
        Fernet(key.encode())
        out.append(key)
    except Exception:
        print("TOKEN_ENCRYPTION_KEYS entry is not a Fernet key; using a key derived from it.", file=sys.stderr)
        out.append(base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest()).decode())
print(",".join(out))
PY
)"
export TOKEN_ENCRYPTION_KEYS

cd /app/backend
# Create or upgrade the database (SQLite on the volume; upstream copies it aside before a migration).
python -m app.server migrate
# Set the owner passphrase from SUPARAGENT_OWNER_PASSPHRASE (first start, or after you change the variable).
python /usr/local/lib/railway_bootstrap_owner.py
exec python -m app.server
