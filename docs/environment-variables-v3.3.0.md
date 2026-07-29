# 환경변수 입력 순서

Preview와 Production은 DB·Blob·Queue·공유 비밀을 분리합니다. 한 환경의 값이 다른 환경에 섞이면 사용자 파일과 작업이 교차할 수 있습니다.

## 1. Development

로컬 `.env`에 입력합니다.

| 변수 | 값 |
|---|---|
| `DATABASE_URL` | 로컬 PostgreSQL |
| `APP_BASE_URL` | `http://localhost:3000` |
| `WORKER_SHARED_SECRET` | 로컬 전용 난수 |
| `STORAGE_DRIVER` | `local` |
| `NEXT_PUBLIC_STORAGE_DRIVER` | `local` |
| `LOCAL_BLOB_DIR` | `../../runtime/blob` |
| `QUEUE_DRIVER` | `local` |
| `MAX_UPLOAD_BYTES` | `26214400` |

검사:

```bash
node scripts/check-env.mjs .env
```

## 2. Preview

Vercel Project Settings의 Preview 환경에 다음 순서로 입력합니다.

1. `DATABASE_URL`
2. `WORKER_SHARED_SECRET`
3. `STORAGE_DRIVER=vercel`
4. `NEXT_PUBLIC_STORAGE_DRIVER=vercel`
5. `BLOB_READ_WRITE_TOKEN`
6. `QUEUE_DRIVER=vercel`
7. `VERCEL_QUEUE_REGION=icn1`
8. `VERCEL_QUEUE_TOPIC=handfont-preview-jobs`
9. `MAX_UPLOAD_BYTES=26214400`

`APP_BASE_URL`은 생략할 수 있습니다. 앱은 Vercel 시스템 URL을 자동 사용합니다. 고정 Preview 도메인을 사용할 때만 명시합니다.

Preview 워커에는 다음을 입력합니다.

- `CONTROL_API_BASE_URL=https://<preview-domain>`
- Preview 웹과 동일한 `WORKER_SHARED_SECRET`
- Preview 웹과 동일한 `BLOB_READ_WRITE_TOKEN`
- `WORKER_STORAGE_DRIVER=vercel`
- `QUEUE_DRIVER=vercel`
- `VERCEL_QUEUE_REGION=icn1`
- `VERCEL_QUEUE_TOPIC=handfont-preview-jobs`
- `QUEUE_CONSUMER_GROUP=font-engine-preview-v1`
- `WORKER_RUNTIME_DIR=/tmp/handfont-worker`

## 3. Production

Preview 검증이 끝난 뒤 별도 값을 생성합니다.

1. Production DB 생성·연결
2. Production Private Blob 생성·연결
3. Production Queue topic 결정
4. 새 `WORKER_SHARED_SECRET` 생성
5. Vercel Production 환경에 입력
6. Production 워커에 같은 값 입력
7. 웹과 워커 재배포

Production 값:

- `DATABASE_URL`
- `WORKER_SHARED_SECRET`
- `STORAGE_DRIVER=vercel`
- `NEXT_PUBLIC_STORAGE_DRIVER=vercel`
- `BLOB_READ_WRITE_TOKEN`
- `QUEUE_DRIVER=vercel`
- `VERCEL_QUEUE_REGION=icn1`
- `VERCEL_QUEUE_TOPIC=handfont-production-jobs`
- `MAX_UPLOAD_BYTES=26214400`

## 공유 비밀 생성

```bash
node scripts/generate-worker-secret.mjs
```

Preview와 Production에서 서로 다른 값을 사용합니다.

## 변경 규칙

- Vercel 환경변수를 변경하면 새 배포가 필요합니다.
- 워커 공유 비밀 또는 Blob 토큰을 변경하면 웹과 워커를 함께 재배포합니다.
- `.env.preview.example`과 `.env.production.example`에는 실제 값을 기록하지 않습니다.
