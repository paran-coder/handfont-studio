from worker.models import QueueMessage

def test_queue_message_contract():
    item=QueueMessage.model_validate({'schemaVersion':'3.3.0','jobId':'job_1','projectId':'prj_1','kind':'process','idempotencyKey':'key','callbackBaseUrl':'http://localhost:3000'})
    assert item.kind=='process'
