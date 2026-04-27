#!/usr/bin/env bash
# =============================================================================
# NovaSight S3 / Iceberg bucket bootstrap
# =============================================================================
# Creates per-tenant Iceberg buckets and applies the lifecycle policy.
# Works against any S3-compatible endpoint (AWS S3, MinIO, R2).
#
# Usage:
#   ./init-buckets.sh                   # Creates buckets for all known tenants
#   ./init-buckets.sh demo acme-corp    # Creates buckets for given tenant slugs
#
# Required env (see s3.env.example):
#   S3_ENDPOINT_URL, AWS_REGION,
#   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
# =============================================================================
set -euo pipefail

ENDPOINT="${S3_ENDPOINT_URL:-http://localhost:9000}"
REGION="${AWS_REGION:-us-east-1}"
ALIAS="${MC_ALIAS:-novasight}"
BUCKET_PREFIX="${S3_BUCKET_PREFIX:-novasight-}"

if ! command -v mc >/dev/null 2>&1; then
  echo "ERROR: 'mc' (MinIO client) is required" >&2
  exit 1
fi

mc alias set "$ALIAS" "$ENDPOINT" \
  "${AWS_ACCESS_KEY_ID:-minioadmin}" \
  "${AWS_SECRET_ACCESS_KEY:-minioadmin}" >/dev/null

slugs=("$@")
if [[ ${#slugs[@]} -eq 0 ]]; then
  slugs=("novasight-demo" "acme-corp")
fi

for slug in "${slugs[@]}"; do
  bucket="${BUCKET_PREFIX}${slug}"
  if ! mc ls "$ALIAS/$bucket" >/dev/null 2>&1; then
    mc mb --region "$REGION" "$ALIAS/$bucket"
    echo "Created bucket: $bucket"
  else
    echo "Bucket exists:   $bucket"
  fi

  # Apply lifecycle (noop if already applied with same JSON)
  if [[ -f "$(dirname "$0")/lifecycle-policy.json" ]]; then
    mc ilm import "$ALIAS/$bucket" < "$(dirname "$0")/lifecycle-policy.json" \
      || echo "WARN: failed to apply lifecycle on $bucket"
  fi

  # Block any anonymous access
  mc anonymous set none "$ALIAS/$bucket" >/dev/null
done

echo "S3 / Iceberg bucket initialization complete."
