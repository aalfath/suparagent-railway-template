# Suparagent on Railway: the official server image, pinned by version and digest, plus a small start script
# and two engine CLIs (Claude Code and Codex), installed the way upstream's ENGINES build argument does.
# Upstream: https://github.com/Anil-matcha/suparagent (Apache-2.0), image from its "Server image" workflow.

# Engine CLIs, built in a throwaway home folder and copied as a plain tree with their own Node, as upstream does.
FROM node:22.23.4-bookworm-slim@sha256:5ec23b7c622b00547753bc6ffd78085dd868a68aeb41c8e0a1418f033e13d96d AS engines
ARG ENGINES="@anthropic-ai/claude-code@2.1.328 @openai/codex@0.170.0"
RUN mkdir -p /out/bin /out/lib \
 && HOME=/tmp/build-home npm install -g --prefix /out --no-audit --no-fund $ENGINES \
 && cp "$(command -v node)" /out/bin/node \
 && rm -rf /tmp/build-home /root/.npm

FROM ghcr.io/anil-matcha/suparagent:v0.8.7@sha256:76081103077a8da4637d7c30e97ed72420f0c7322e2fab920472406f7848f79a
COPY --from=engines /out /opt/engines

# The image runs as uid 10001, but Railway mounts volumes owned by root. The start script runs as root
# only long enough to fix the owner of /data, then drops to the image's own user with setpriv.
USER root
COPY --chmod=755 railway/start.sh /usr/local/bin/railway-start.sh
COPY --chmod=644 railway/bootstrap_owner.py /usr/local/lib/railway_bootstrap_owner.py
COPY --chmod=644 railway/serve.py /usr/local/lib/railway_serve.py

# The CLIs are pinned here; updates come through this repo, not from the CLIs updating themselves.
ENV DISABLE_AUTOUPDATER=1

ENTRYPOINT ["tini", "--"]
CMD ["/usr/local/bin/railway-start.sh"]
