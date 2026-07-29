# 폰트 워커 배포 v3.3.0

`workers/font-engine/Dockerfile`을 Docker를 지원하는 실행 환경에 배포합니다.

## 최소 권장 자원

- 2 vCPU
- 2GB RAM
- 2GB 이상 임시 디스크
- 인스턴스당 동시 작업 1개
- 작업 재시작 정책 활성화

## Preview 변수

- `CONTROL_API_BASE_URL=https://<preview-domain>`
- `WORKER_SHARED_SECRET=<preview 웹과 동일>`
- `WORKER_STORAGE_DRIVER=vercel`
- `BLOB_READ_WRITE_TOKEN=<preview Blob token>`
- `QUEUE_DRIVER=vercel`
- `VERCEL_QUEUE_REGION=icn1`
- `VERCEL_QUEUE_TOPIC=handfont-preview-jobs`
- `QUEUE_CONSUMER_GROUP=font-engine-preview-v1`
- `WORKER_RUNTIME_DIR=/tmp/handfont-worker`

## Production 변수

Preview와 별도의 웹 URL, 공유 비밀, Blob token, Queue topic을 사용합니다.

## 배포 확인

1. 컨테이너가 정상 시작되는지 확인합니다.
2. Queue 연결 로그를 확인합니다.
3. Preview 웹에서 분석 작업을 등록합니다.
4. 워커가 작업을 임대하고 진행률을 콜백하는지 확인합니다.
5. 결과 Blob과 DB 상태가 업데이트되는지 확인합니다.
6. 작업 실패 시 재시도 횟수와 최종 실패 상태를 확인합니다.
