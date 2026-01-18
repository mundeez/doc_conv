#!/usr/bin/env bash
set -euo pipefail

# Simple wrapper to run pandoc in a disposable container.
# Usage: set PANDOC_BIN="./scripts/pandoc_docker.sh" and call pandoc as usual.
# Optional: PANDOC_IMAGE (default pandoc/core:3.1)

IMAGE="${PANDOC_IMAGE:-pandoc/core:3.1}"
ROOT="${PANDOC_ROOT:-$(pwd)}"

exec docker run --rm \
  -v "${ROOT}":/data \
  -w /data \
  "${IMAGE}" "$@"
