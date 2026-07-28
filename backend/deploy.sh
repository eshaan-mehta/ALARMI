#!/usr/bin/env bash
# ALARMI backend → Azure Container Apps, one-shot manual deploy.
#
# Builds the Docker image in ACR (cloud build, no local Docker daemon), then
# points an existing Container App at it. Idempotent: rerun after every change.
#
#   cd backend && ./deploy.sh
#
# Assumes the resource group, Container App, and its managed environment already
# exist (created once in the portal). This script only builds + wires the image.
# Auth: run `az login` first — interactive, can't live in a script.
#
# Override any of these inline, e.g. `APP=my-api ./deploy.sh`:
set -euo pipefail

SUB="${SUB:-Azure for Students}"   # subscription name or id
RG="${RG:-rg-alarmi}"              # resource group
APP="${APP:-alarmi-api}"           # Container App name (portal-created)
IMAGE="${IMAGE:-alarmi-api}"       # image repo name inside ACR
PORT="${PORT:-8000}"               # container listen port (uvicorn)

cd "$(dirname "$0")"  # run from backend/ regardless of caller's cwd

# --- preflight ---
command -v az >/dev/null || { echo "az CLI not found. Install it or use Cloud Shell."; exit 1; }
az account show >/dev/null 2>&1 || { echo "Not logged in. Run: az login"; exit 1; }
[ -f Dockerfile ] || { echo "No Dockerfile in $(pwd). Run from backend/."; exit 1; }

echo "==> Subscription: $SUB"
az account set --subscription "$SUB"

# --- registry: reuse the first ACR in the RG, else create one ---
# ACR names are globally unique + immutable, so we can't hardcode. Discover it.
ACR="$(az acr list -g "$RG" --query "[0].name" -o tsv 2>/dev/null || true)"
if [ -z "$ACR" ]; then
  ACR="alarmiacr$RANDOM"
  echo "==> No registry in $RG. Creating $ACR (Basic, admin enabled)"
  az acr create -g "$RG" -n "$ACR" --sku Basic --admin-enabled true -o none
else
  echo "==> Reusing registry: $ACR"
  # ensure admin user is on (needed for the pull creds below)
  az acr update -n "$ACR" --admin-enabled true -o none
fi
LOGIN_SERVER="$(az acr show -n "$ACR" --query loginServer -o tsv)"
TAG="$(git rev-parse --short HEAD 2>/dev/null || date +%s)"  # traceable image tag

# --- build + push (cloud-side, uses ./ as context) ---
echo "==> Building $LOGIN_SERVER/$IMAGE:$TAG in ACR (this uploads ./ as context)"
az acr build --registry "$ACR" --image "$IMAGE:$TAG" --image "$IMAGE:latest" \
  --file Dockerfile . -o none

# --- give the app pull creds (admin user; role-assignment path is blocked) ---
echo "==> Setting registry pull credentials on $APP"
az containerapp registry set -g "$RG" -n "$APP" \
  --server "$LOGIN_SERVER" \
  --username "$(az acr credential show -n "$ACR" --query username -o tsv)" \
  --password "$(az acr credential show -n "$ACR" --query 'passwords[0].value' -o tsv)" \
  -o none

# --- swap image + fix ingress port ---
echo "==> Deploying $IMAGE:$TAG and setting ingress port $PORT"
az containerapp update -g "$RG" -n "$APP" --image "$LOGIN_SERVER/$IMAGE:$TAG" -o none
az containerapp ingress update -g "$RG" -n "$APP" --target-port "$PORT" -o none

# --- report ---
FQDN="$(az containerapp show -g "$RG" -n "$APP" --query properties.configuration.ingress.fqdn -o tsv)"
echo
echo "==> Deployed. https://$FQDN/docs"
