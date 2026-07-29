# Vercel 배포 절차 v3.3.0

## 1. 프로젝트 Import

1. Vercel에서 GitHub 저장소를 Import합니다.
2. Framework Preset은 Next.js를 선택합니다.
3. Root Directory는 `apps/web`으로 지정합니다.
4. Root Directory 밖 소스 포함 옵션을 활성화합니다. `packages/contracts`가 빌드에 필요합니다.
5. Production Branch는 `main`으로 설정합니다.
6. 초기에는 Deployment Protection을 활성화합니다.

참고 설정은 `infrastructure/vercel/project-settings-v3.3.0.json`에 있습니다.

## 2. Build 설정

- Node.js: 22.x
- Install Command: `cd ../.. && corepack enable && pnpm install --frozen-lockfile`
- Build Command: `cd ../.. && pnpm --filter @handfont/web build`
- Output Directory: `.next`

`pnpm-lock.yaml`이 최초 Push에 포함되어 있어야 합니다.

## 3. 리소스 연결

1. PostgreSQL 공급자를 연결합니다.
2. Private Vercel Blob store를 생성합니다.
3. Vercel Queue를 활성화합니다.
4. Preview와 Production 리소스를 분리합니다.

## 4. 환경변수

`docs/environment-variables-v3.3.0.md`를 따릅니다. 환경변수 변경은 기존 배포에 소급 적용되지 않으므로 변경 후 재배포합니다.

## 5. DB 마이그레이션

Preview DB부터 실행합니다.

```bash
DATABASE_URL='<preview-url>' pnpm --filter @handfont/web db:migrate
```

Production은 Preview 검증 후 별도로 실행합니다.

```bash
DATABASE_URL='<production-url>' pnpm --filter @handfont/web db:migrate
```

## 6. Preview 검증

- 프로젝트 생성
- Private Blob 직접 업로드
- Queue 작업 생성
- 워커 처리
- 글리프 반영
- TTF 결과 다운로드

`docs/post-deploy-smoke-test-v3.3.0.md`의 체크리스트를 사용합니다.

## 7. Production 승격

Preview에서 동일 Commit SHA를 검증한 뒤 Production으로 배포합니다. Production은 별도 환경변수를 사용하므로 승격 후 다시 스모크 테스트합니다.

## 공식 참고 문서

- Git 배포: https://vercel.com/docs/git
- Monorepo: https://vercel.com/docs/monorepos
- Monorepo Root Directory FAQ: https://vercel.com/docs/monorepos/monorepo-faq
- 환경변수: https://vercel.com/docs/environment-variables
- 시스템 환경변수: https://vercel.com/docs/environment-variables/system-environment-variables
- Private Blob: https://vercel.com/docs/vercel-blob/private-storage
- Client Upload: https://vercel.com/docs/vercel-blob/client-upload
