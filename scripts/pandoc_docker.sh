#!/usr/bin/env bash
set -euo pipefail

# Simple wrapper to run pandoc in a disposable container.
# Usage: set PANDOC_BIN="./scripts/pandoc_docker.sh" and call pandoc as usual.
# Optional: PANDOC_IMAGE (default pandoc/core:3.1)

IMAGE="${PANDOC_IMAGE:-pandoc/core:3.1}"
ROOT="${PANDOC_ROOT:-$(pwd)}"

# Mount project root at /app so absolute paths like /app/uploads/... remain valid.
exec docker run --rm \
  -v "${ROOT}":/app \
  -w /app \
  "${IMAGE}" "$@"
