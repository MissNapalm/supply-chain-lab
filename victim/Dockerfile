# Victim "CI build agent". It installs dependencies from the internal
# registry when the container starts — that install is when the payload fires.
FROM python:3.12-slim

# A secret injected into the build env, as CI systems commonly do.
ENV CI_DEPLOY_TOKEN="prod-deploy-key-8f3a9c2e-DO-NOT-LEAK"

# Real CI build agents run as an UNPRIVILEGED user, not root. Running the install
# as this user is what makes the beacon's `id` output accurate: install-time code
# runs as whoever runs the install — it does not need, and usually does not have,
# root. (The damage — reading CI_DEPLOY_TOKEN — needs no privilege at all.)
RUN useradd --create-home --shell /bin/sh ci
ENV PATH="/home/ci/.local/bin:${PATH}"

WORKDIR /app
COPY requirements.txt entrypoint.sh ./
RUN chmod +x entrypoint.sh && chown -R ci:ci /app

USER ci
ENTRYPOINT ["./entrypoint.sh"]
