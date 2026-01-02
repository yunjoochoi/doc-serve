#!/bin/bash

# Stop any existing container
docker stop docling-hack-container 2>/dev/null
docker rm docling-hack-container 2>/dev/null

# Run with source code mounted (development mode)
docker run --rm \
  --name docling-hack-container \
  -p 5001:5001 \
  -e DOCLING_SERVE_ENG_KIND=local \
  -e DOCLING_SERVE_ENG_LOC_SHARE_MODELS=true \
  -e DOCLING_SERVE_ARTIFACTS_PATH=/opt/app-root/src/.cache/docling/models \
  -e HF_HUB_OFFLINE=1 \
  -v /mnt/c/Users/ychoi191/work/docling-serve/docling-models-exports:/opt/app-root/src/.cache/docling/models:z \
  -v /mnt/c/Users/ychoi191/work/docling-serve/docling_serve:/opt/app-root/src/docling_serve:z \
  -v /mnt/c/Users/ychoi191/work/docling-jobkit/docling_jobkit:/opt/app-root/lib/python3.12/site-packages/docling_jobkit:z \
  docling-hack
