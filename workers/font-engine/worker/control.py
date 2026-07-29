from __future__ import annotations
from typing import Any
import httpx
from .config import settings
class ControlClient:
    def __init__(self, base_url: str|None=None, secret: str|None=None):
        self.base_url=(base_url or settings.control_api_base_url).rstrip('/')
        self.headers={'x-handfont-worker-secret':secret or settings.worker_secret}
    def manifest(self,job_id:str)->dict[str,Any]:
        with httpx.Client(timeout=30) as c:
            r=c.get(f'{self.base_url}/api/internal/jobs/{job_id}/manifest',headers=self.headers);r.raise_for_status();return r.json()
    def progress(self,job_id:str,value:int,message:str)->None:
        with httpx.Client(timeout=30) as c:
            r=c.post(f'{self.base_url}/api/internal/jobs/{job_id}/progress',headers=self.headers,json={'progress':value,'message':message});r.raise_for_status()
    def complete(self,job_id:str,result:dict[str,Any],glyphs:list[dict[str,Any]]|None=None,artifact_url:str|None=None)->None:
        with httpx.Client(timeout=60) as c:
            r=c.post(f'{self.base_url}/api/internal/jobs/{job_id}/complete',headers=self.headers,json={'result':result,'glyphs':glyphs,'artifactUrl':artifact_url});r.raise_for_status()
    def fail(self,job_id:str,error:str,message:str='작업이 실패했습니다.')->None:
        with httpx.Client(timeout=30) as c:
            c.post(f'{self.base_url}/api/internal/jobs/{job_id}/fail',headers=self.headers,json={'error':error,'message':message}).raise_for_status()
    def lease(self)->dict[str,Any]|None:
        with httpx.Client(timeout=30) as c:
            r=c.post(f'{self.base_url}/api/internal/worker/lease',headers=self.headers);r.raise_for_status();return r.json().get('job')
