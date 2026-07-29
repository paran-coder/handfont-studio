# HandFont Studio v3.3.6

손글씨 작성 양식을 내려받고, 작성본을 업로드해 SVG 글리프와 TTF 폰트로 변환하는 GitHub·Vercel 배포형 모노레포입니다.

## v3.3.6 주요 기능

- 로그인 없이 브라우저마다 고유한 익명 소유권 자동 발급
- 프로젝트 목록·상세·삭제를 현재 브라우저 소유 프로젝트로 제한
- 업로드, 분석 작업, 결과 다운로드와 Blob 접근에 소유권 검사 적용
- 쿠키 원문은 DB에 저장하지 않고 SHA-256 해시만 저장
- 다른 소유자의 프로젝트 ID를 알아도 404로 처리
- 기존 작성 양식 다운로드, 프로젝트 삭제, 결과 재다운로드 기능 유지

## 구성

- `apps/web`: Next.js App Router 웹 UI와 제어 API
- `apps/web/proxy.ts`: 익명 소유자 쿠키 발급
- `apps/web/lib/owner.ts`: 소유자 토큰 검증·해시
- `apps/web/public/templates`: 사용자 데이터가 없는 작성 양식 자산
- `workers/font-engine`: 독립 Docker Python 폰트 워커
- `packages/contracts`: 웹·워커 공용 계약
- `infrastructure/migrations`: PostgreSQL 마이그레이션
- `scripts`: 저장소·환경변수·개인정보 사전 검사

## 로컬 실행

```bash
cp .env.example .env
corepack enable
pnpm install
pnpm db:migrate
pnpm dev
```

## Vercel 배포 설정

- Root Directory: `apps/web`
- Include files outside the root directory: Enabled
- Install Command: `cd ../.. && corepack prepare pnpm@10.14.0 --activate && pnpm install`
- Build Command: `cd ../.. && pnpm --filter @handfont/web build`
- 필수 환경변수: `DATABASE_URL`, `WORKER_SHARED_SECRET`
- 운영 기능용 연결: Private Vercel Blob, Queue, 외부 Python 워커

## v3.3.6 데이터베이스 마이그레이션

기능은 기존 `projects.owner_id` 열을 그대로 사용하므로 즉시 동작합니다. 트래픽이 늘기 전 Neon SQL Editor에서 다음 파일을 한 번 실행하면 소유자별 목록 조회 인덱스가 추가되고, 새 프로젝트의 공용 기본값도 제거됩니다.

```text
infrastructure/migrations/0002_anonymous_ownership.sql
```

기존 `owner_id='anonymous'` 프로젝트는 보안상 새 브라우저에 자동 이전하지 않습니다.

## 익명 프로젝트의 특성

프로젝트는 로그인 계정이 아니라 현재 브라우저의 보안 쿠키에 연결됩니다. 같은 브라우저에서는 다시 접속해도 프로젝트가 보이지만, 브라우저 데이터 삭제·시크릿 모드·다른 기기에서는 기존 프로젝트에 접근할 수 없습니다.

## 안전장치

```bash
pnpm privacy:check
pnpm repo:check
pnpm test
```
