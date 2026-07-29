from __future__ import annotations
import mimetypes, shutil
from pathlib import Path
from urllib.parse import urlparse
from .config import settings
class Storage:
    def download(self,url:str,target:Path)->Path: raise NotImplementedError
    def upload(self,source:Path,pathname:str,content_type:str|None=None)->str: raise NotImplementedError
class LocalStorage(Storage):
    def __init__(self,root:Path|None=None): self.root=(root or settings.blob_dir).resolve();self.root.mkdir(parents=True,exist_ok=True)
    def _path(self,url_or_path:str)->Path:
        raw=url_or_path.removeprefix('local://').lstrip('/')
        path=(self.root/raw).resolve()
        if self.root not in path.parents and path!=self.root: raise ValueError('storage path escape')
        return path
    def download(self,url:str,target:Path)->Path: target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(self._path(url),target);return target
    def upload(self,source:Path,pathname:str,content_type:str|None=None)->str:
        target=self._path(pathname);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target);return f'local://{pathname}'
class VercelBlobStorage(Storage):
    def __init__(self,token:str|None=None):
        from vercel.blob import BlobClient
        self.client=BlobClient(token=token or settings.blob_token)
    def download(self,url:str,target:Path)->Path: target.parent.mkdir(parents=True,exist_ok=True);self.client.download_file(url,str(target),overwrite=True);return target
    def upload(self,source:Path,pathname:str,content_type:str|None=None)->str:
        uploaded=self.client.upload_file(str(source),pathname,access='private',content_type=content_type or mimetypes.guess_type(source.name)[0] or 'application/octet-stream',add_random_suffix=False);return uploaded.url
    def close(self): self.client.close()
def get_storage()->Storage: return LocalStorage() if settings.storage_driver=='local' else VercelBlobStorage()
