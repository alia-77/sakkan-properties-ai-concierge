#!/usr/bin/env bash
set -e
python - <<'PY'
from qdrant_client import QdrantClient
from src.settings import QDRANT_URL,QDRANT_API_KEY,COLLECTION,ROOT
c=QdrantClient(url=QDRANT_URL,api_key=QDRANT_API_KEY)
if c.collection_exists(COLLECTION): c.delete_collection(COLLECTION)
import shutil
shutil.rmtree(ROOT/"mem0_store",ignore_errors=True)
PY
python -m src.ingest_qdrant
