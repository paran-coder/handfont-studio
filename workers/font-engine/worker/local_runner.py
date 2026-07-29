from __future__ import annotations
import json,time
from .config import settings
from .control import ControlClient
from .main import run_message

def main():
    client=ControlClient()
    while True:
        job=client.lease()
        if not job:time.sleep(float(__import__('os').getenv('POLL_INTERVAL_SECONDS','2')));continue
        run_message({'schemaVersion':'3.3.0','jobId':job['id'],'projectId':job['project_id'],'kind':job['kind'],'idempotencyKey':job['idempotency_key'],'callbackBaseUrl':settings.control_api_base_url},client)
if __name__=='__main__':main()
