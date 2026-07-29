# 폰트 워커 배포

`workers/font-engine/Dockerfile`을 Railway, Render, Fly.io, Google Cloud Run Jobs 또는 자체 Docker 서버에 배포합니다.

필수 환경변수:

- `CONTROL_API_BASE_URL=https://<vercel-domain>`
- `WORKER_SHARED_SECRET=<web과 동일>`
- `WORKER_STORAGE_DRIVER=vercel`
- `BLOB_READ_WRITE_TOKEN=<같은 private blob store>`
- `VERCEL_QUEUE_REGION=icn1`
- `VERCEL_QUEUE_TOPIC=handfont-jobs`
- `QUEUE_CONSUMER_GROUP=font-engine-v1`
- `QUEUE_DRIVER=vercel`

워커에는 최소 2 vCPU, 2GB RAM, 2GB 이상의 임시 디스크를 권장합니다. 동시 처리 수는 처음에는 인스턴스당 1개로 제한합니다.
