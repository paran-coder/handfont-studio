from pathlib import Path
from worker.storage import LocalStorage

def test_local_storage_roundtrip(tmp_path:Path):
    storage=LocalStorage(tmp_path/'blob');source=tmp_path/'a.txt';source.write_text('hello',encoding='utf-8');url=storage.upload(source,'projects/p/a.txt','text/plain');target=tmp_path/'out.txt';storage.download(url,target);assert target.read_text()=='hello'
def test_local_storage_blocks_escape(tmp_path:Path):
    storage=LocalStorage(tmp_path/'blob')
    try:storage._path('../../escape')
    except ValueError:pass
    else:raise AssertionError('escape must fail')
