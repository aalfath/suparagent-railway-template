"""Start Suparagent's server (`python -m app.server`) with the visitor's real address on Railway.

Railway's edge reaches the container from 100.64.0.0/10 and sends `X-Forwarded-For: <visitor>, <CDN hop>`.
Uvicorn takes the right-most address it doesn't trust, which is the CDN hop, and that hop changes
between requests. Suparagent counts failed sign-ins per address, so without this every visitor behind
one CDN node would share a lockout, and an attacker would get 5 tries per CDN node.

Railway's edge overwrites `X-Real-IP` with the visitor's address (a value the visitor sends is
dropped). So, only for a request whose socket peer is Railway's edge (RAILWAY_EDGE_CIDR), this
replaces `X-Forwarded-For` with that one address before Uvicorn's own proxy-header handling runs, with
the same trusted list the server would use. Anything else is passed on unchanged.
"""

import ipaddress
import os
import sys

sys.path.insert(0, os.environ.get("SUPARAGENT_BACKEND_DIR", "/app/backend"))

import uvicorn  # noqa: E402
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware  # noqa: E402

EDGE = [ipaddress.ip_network(n.strip()) for n in os.environ.get("RAILWAY_EDGE_CIDR", "100.64.0.0/10").split(",") if n.strip()]


def _from_edge(scope) -> bool:
    client = scope.get("client")
    if not client:
        return False
    try:
        address = ipaddress.ip_address(client[0])
    except ValueError:
        return False
    if address.version == 6 and address.ipv4_mapped:
        address = address.ipv4_mapped
    return any(address in network for network in EDGE)


class RealIPFromEdge:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket") and _from_edge(scope):
            headers = scope.get("headers", [])
            real = [value for key, value in headers if key == b"x-real-ip"]
            if len(real) == 1:
                try:
                    visitor = str(ipaddress.ip_address(real[0].decode("latin-1").strip()))
                except ValueError:
                    visitor = None
                if visitor:
                    headers = [(k, v) for k, v in headers if k != b"x-forwarded-for"]
                    headers.append((b"x-forwarded-for", visitor.encode()))
                    scope = dict(scope, headers=headers)
        return await self.app(scope, receive, send)


_run = uvicorn.run


def run(app, **kwargs):
    if kwargs.get("proxy_headers"):
        trusted = kwargs.get("forwarded_allow_ips") or "127.0.0.1"
        app = RealIPFromEdge(ProxyHeadersMiddleware(app, trusted_hosts=trusted))
        kwargs["proxy_headers"] = False
    return _run(app, **kwargs)


uvicorn.run = run

from app.server.entry import main  # noqa: E402

sys.exit(main())
