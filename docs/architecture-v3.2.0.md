# v3.2.0 배포 아키텍처

```text
Browser
  ├─ Next.js UI/API (Vercel)
  ├─ direct upload ───────────────► Private Vercel Blob
  └─ create job ─► PostgreSQL ─► Vercel Queues
                                      │
                                      ▼
                              Docker Font Worker
                               ├─ Blob download
                               ├─ OpenCV/vectorize
                               ├─ TTF build/validate
                               └─ Blob upload + API callback
```

웹 요청은 CPU 작업을 직접 수행하지 않습니다. 작업 생성 API는 PostgreSQL에 작업을 기록한 뒤 큐 메시지를 발행하고 즉시 작업 ID를 반환합니다. 워커는 at-least-once 전달을 전제로 동일 작업 ID의 경로를 사용하며, 완료 API는 이미 완료된 작업을 다시 적용하지 않습니다.
