#!/usr/bin/env bash
# ALARMI backend → Google Cloud Run, one-shot manual deploy.
#
# Builds from source (Cloud Build reads ./Dockerfile) and deploys the service.
# Idempotent: rerun after every change. Auth: run `gcloud auth login` first.
#
#   cd backend && PROJECT=<gcp-project-id> ./deploy.sh
#
# Override any of these inline, e.g. `REGION=us-east1 ./deploy.sh`:
set -euo pipefail

PROJECT="${PROJECT:?set PROJECT=alarmi-fa0c6}"
REGION="${REGION:-us-east1}"
SERVICE="${SERVICE:-alarmi-api}"
BUCKET="${BUCKET:-}"              # GCS bucket for blobs; empty → FakeBlobStore
DATABASE_URL="${DATABASE_URL:-}" # Cloud SQL URL; empty → ephemeral SQLite in the container
CLOUDSQL="${CLOUDSQL:-}"         # Cloud SQL connection name (proj:region:inst); empty → none

cd "$(dirname "$0")"  # run from backend/ regardless of caller's cwd

command -v gcloud >/dev/null || { echo "gcloud not found. Install the Cloud SDK or use Cloud Shell."; exit 1; }
[ -f Dockerfile ] || { echo "No Dockerfile in $(pwd). Run from backend/."; exit 1; }

echo "==> Project: $PROJECT  Region: $REGION  Service: $SERVICE"
gcloud config set project "$PROJECT" >/dev/null

# Runtime env, using a custom ^@@^ delimiter so a DATABASE_URL with '=' or '?'
# passes through cleanly. Empty DATABASE_URL/BUCKET → ephemeral SQLite +
# FakeBlobStore (data resets on redeploy).
ENV="^@@^APP_ENV=cloudrun"
[ -n "$BUCKET" ]       && ENV="$ENV@@GCS_BUCKET=$BUCKET"
[ -n "$DATABASE_URL" ] && ENV="$ENV@@DATABASE_URL=$DATABASE_URL"

# Attach the Cloud SQL instance (mounts its socket at /cloudsql/<name>) if given.
CLOUDSQL_FLAG=()
[ -n "$CLOUDSQL" ] && CLOUDSQL_FLAG=(--add-cloudsql-instances "$CLOUDSQL")

echo "==> Building from source + deploying (Cloud Build reads ./Dockerfile)"
# --no-cpu-throttling keeps CPU allocated after the HTTP response so the
# in-process background job (IFC processing) actually finishes. min=max 1 keeps
# a single always-warm instance, so a job isn't orphaned by scale-down and the
# in-process worker isn't split across replicas (see app/processing/queue.py —
# swap to Cloud Tasks when durable, multi-instance processing is needed).
gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --no-cpu-throttling \
  --min-instances 1 \
  --max-instances 1 \
  "${CLOUDSQL_FLAG[@]}" \
  --set-env-vars "$ENV"

URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')"
echo
echo "==> Deployed. $URL/api/health"
