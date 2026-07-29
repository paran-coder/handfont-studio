# API 계약 v3.3.1

v3.3.1의 웹·워커 메시지 `schemaVersion`은 `3.3.0`입니다.

## 작업 메시지

```json
{
  "schemaVersion": "3.3.0",
  "jobId": "job_...",
  "projectId": "prj_...",
  "kind": "process",
  "idempotencyKey": "...",
  "callbackBaseUrl": "https://preview.example"
}
```

`kind`는 `process` 또는 `export`입니다.

## 내부 API 인증

워커는 내부 API 요청에 다음 Header를 보냅니다.

```text
x-handfont-worker-secret: <WORKER_SHARED_SECRET>
```

웹은 timing-safe 비교를 수행합니다.

## 환경별 계약

Preview 메시지는 Preview Queue·DB·Blob·공유 비밀만 사용합니다. Production과 자격증명을 공유하지 않습니다.
