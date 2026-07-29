from __future__ import annotations
import argparse,json,shutil,traceback
from pathlib import Path
from .config import settings
from .control import ControlClient
from .engine_adapter import process,export
from .models import QueueMessage
from .storage import get_storage

def run_message(raw:dict,control:ControlClient|None=None)->dict:
    message=QueueMessage.model_validate(raw);control=control or ControlClient(message.callbackBaseUrl);storage=get_storage();work=settings.runtime_dir/message.jobId
    try:
        manifest=control.manifest(message.jobId)
        def progress(v:int,m:str):control.progress(message.jobId,v,m)
        if message.kind=='process':result,glyphs=process(manifest,storage,work,progress);control.complete(message.jobId,result,glyphs=glyphs)
        else:result,artifact=export(manifest,storage,work,progress);control.complete(message.jobId,result,artifact_url=artifact)
        return {'ok':True,'jobId':message.jobId,'result':result}
    except Exception as exc:
        control.fail(message.jobId,f'{type(exc).__name__}: {exc}\n{traceback.format_exc()}')
        return {'ok':False,'jobId':message.jobId,'error':str(exc)}
    finally:
        if hasattr(storage,'close'):storage.close()
        shutil.rmtree(work,ignore_errors=True)
def main():
    p=argparse.ArgumentParser();p.add_argument('--message',required=True);args=p.parse_args();result=run_message(json.loads(args.message));print(json.dumps(result,ensure_ascii=False));raise SystemExit(0 if result['ok'] else 1)
if __name__=='__main__':main()
