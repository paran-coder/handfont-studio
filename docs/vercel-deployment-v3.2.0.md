# GitHub → Vercel 배포 절차

1. 이 폴더를 GitHub 저장소의 루트로 올립니다.
2. Vercel에서 저장소를 Import하고 Root Directory를 `apps/web`으로 지정합니다.
3. Vercel Marketplace에서 PostgreSQL 공급자를 연결하고 `DATABASE_URL`을 확인합니다.
4. Private Vercel Blob store를 만들고 `BLOB_READ_WRITE_TOKEN`을 연결합니다.
5. Vercel Queues를 활성화하고 `VERCEL_QUEUE_REGION=icn1`, `VERCEL_QUEUE_TOPIC=handfont-jobs`를 설정합니다.
6. `WORKER_SHARED_SECRET`은 32바이트 이상의 난수로 만들고 웹과 워커에 동일하게 설정합니다.
7. 최초 한 번 `pnpm --filter @handfont/web db:migrate`를 실행합니다.
8. `main` 브랜치는 Production, Pull Request는 Preview 배포로 사용합니다.

## Vercel 환경변수

- `DATABASE_URL`
- `APP_BASE_URL`
- `WORKER_SHARED_SECRET`
- `STORAGE_DRIVER=vercel`
- `NEXT_PUBLIC_STORAGE_DRIVER=vercel`
- `BLOB_READ_WRITE_TOKEN`
- `QUEUE_DRIVER=vercel`
- `VERCEL_QUEUE_REGION=icn1`
- `VERCEL_QUEUE_TOPIC=handfont-jobs`
- `MAX_UPLOAD_BYTES=26214400`
