#!/bin/bash
set -e
cd "$(dirname "$0")"

IMAGE="yasma:latest"
ARCHIVE="docker/yasma.tar.gz"

echo "Building $IMAGE..."
docker build -t "$IMAGE" -f docker/Dockerfile .

echo "Exporting to $ARCHIVE using pigz (parallel compression)..."
docker save "$IMAGE" | pigz -1 -p $(nproc) > "$ARCHIVE"

echo "Cleaning up dangling images..."
docker image prune -f

echo "Done: $ARCHIVE ($(du -h $ARCHIVE | cut -f1))"
