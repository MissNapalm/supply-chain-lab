#!/bin/sh
set -e

echo "[victim] Waiting for internal registry..."
until python -c "import urllib.request,sys; urllib.request.urlopen('http://registry:8080/', timeout=2)" 2>/dev/null; do
    sleep 1
done

echo "[victim] Waiting for deploy-api..."
until python -c "import urllib.request,sys; urllib.request.urlopen('http://deploy-api:9000/health', timeout=2)" 2>/dev/null; do
    sleep 1
done

# Obtain a REAL deploy credential at build start, the way a CI job fetches one
# from its secrets store / OIDC provider. This live JWT is what sits in the
# build env -- and what the install hook is about to steal.
echo "[victim] Fetching deploy credential from deploy-api..."
export CI_DEPLOY_TOKEN="$(python -c "import urllib.request,json; print(json.load(urllib.request.urlopen('http://deploy-api:9000/token', timeout=4))['token'])")"
echo "[victim] CI_DEPLOY_TOKEN is set (a live, signed deploy JWT)."
echo

echo "[victim] Installing dependencies from internal registry..."
echo "[victim] (this is the moment the supply-chain payload executes)"
echo

# Pull from the internal registry only -> fully offline.
# In a real "dependency confusion" attack the victim would use
# --extra-index-url and the malicious version would simply outrank the real one.
pip install --no-cache-dir --user \
    --index-url http://registry:8080/simple/ \
    --trusted-host registry \
    -r requirements.txt

echo
echo "[victim] Build finished successfully — nothing looks wrong from here:"
python -c "import awesome_utils; print('   app output:', awesome_utils.shout('build complete'))"
echo
echo "[victim] ...but the install hook already beaconed your CI token out. Check the collector."

# Keep the container up so you can inspect it; nothing is running in the
# background (the dummy payload fired once and exited).
tail -f /dev/null
