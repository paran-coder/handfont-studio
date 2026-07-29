from worker.main import run_message
class FakeControl:
    def manifest(self,job_id):raise RuntimeError('boom')
    def progress(self,*a):pass
    def complete(self,*a,**k):pass
    def fail(self,job_id,error,message=''):self.error=error

def test_failure_is_reported(monkeypatch,tmp_path):
    from worker import main as module
    class Storage:
        def close(self):pass
    monkeypatch.setattr(module,'get_storage',lambda:Storage())
    c=FakeControl();result=run_message({'schemaVersion':'3.3.0','jobId':'job_1','projectId':'prj_1','kind':'process','idempotencyKey':'k','callbackBaseUrl':'http://local'},c)
    assert not result['ok'] and 'boom' in c.error
