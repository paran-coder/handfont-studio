from __future__ import annotations
import os
from pathlib import Path
from pydantic import BaseModel
class Settings(BaseModel):
    control_api_base_url: str = os.getenv('CONTROL_API_BASE_URL','http://localhost:3000').rstrip('/')
    worker_secret: str = os.getenv('WORKER_SHARED_SECRET','')
    storage_driver: str = os.getenv('WORKER_STORAGE_DRIVER','local')
    blob_dir: Path = Path(os.getenv('WORKER_BLOB_DIR','../../runtime/blob')).resolve()
    runtime_dir: Path = Path(os.getenv('WORKER_RUNTIME_DIR','../../worker-runtime')).resolve()
    blob_token: str | None = os.getenv('BLOB_READ_WRITE_TOKEN')
settings=Settings()
settings.blob_dir.mkdir(parents=True,exist_ok=True)
settings.runtime_dir.mkdir(parents=True,exist_ok=True)
