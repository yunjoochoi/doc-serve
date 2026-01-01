#!/bin/bash

# Stop any existing container
docker stop docling-hack-container 2>/dev/null
docker rm docling-hack-container 2>/dev/null

# Create local cache directories if they don't exist
mkdir -p /home/shaush/projects/docling-serve/cache/huggingface/hub
mkdir -p /home/shaush/projects/docling-serve/cache/huggingface/modules
mkdir -p /home/shaush/projects/docling-serve/docling-models-exports

# Run with source code mounted (development mode)
docker run --rm \
  --name docling-hack-container \
  -p 5001:5001 \
  -e DOCLING_SERVE_ENG_KIND=local \
  -e DOCLING_SERVE_LAYOUT_BATCH_SIZE=64 \
  -e DOCLING_SERVE_TABLE_BATCH_SIZE=64 \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -v /home/shaush/projects/docling-serve/docling-models-exports:/opt/app-root/src/.cache/huggingface/hub:z \
  -v /home/shaush/projects/docling-serve/docling-models-exports:/opt/app-root/src/.cache/docling/models:z \
  -v /home/shaush/projects/docling-serve/docling_serve:/opt/app-root/src/docling_serve:z \
  -v /home/shaush/projects/docling-jobkit/docling_jobkit:/opt/app-root/lib/python3.12/site-packages/docling_jobkit:z \
  docling-hack
