# HandFont Studio v3.3.4

손글씨 작성 양식을 내려받고, 작성본을 업로드해 SVG 글리프와 TTF 폰트로 변환하는 GitHub·Vercel 배포형 모노레포입니다.

## v3.3.4 주요 기능

- 9페이지 손글씨 작성 양식 PDF 다운로드
- 페이지별 PNG 묶음 ZIP 다운로드
- 프로젝트 목록·상세 화면에서 프로젝트 삭제
- 삭제 시 업로드 이미지, 글리프 SVG·메타데이터, 완성 폰트 파일 정리
- 프로젝트를 다시 연 뒤에도 최신 TTF 결과 재다운로드
- 처리 중 작업이 있는 프로젝트의 실수 삭제 방지

## 구성

- `apps/web`: Next.js App Router 웹 UI와 제어 API
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

다른 터미널에서 워커를 실행합니다.

```bash
cd workers/font-engine
python -m pip install -r requirements.txt
QUEUE_DRIVER=local python -m worker.local_runner
```

## Vercel 배포 설정

- Root Directory: `apps/web`
- Include files outside the root directory: Enabled
- Install Command: `cd ../.. && corepack prepare pnpm@10.14.0 --activate && pnpm install`
- Build Command: `cd ../.. && pnpm --filter @handfont/web build`
- 필수 환경변수: `DATABASE_URL`, `WORKER_SHARED_SECRET`
- 운영 기능용 연결: Private Vercel Blob, Queue, 외부 Python 워커

## 안전장치

```bash
pnpm privacy:check
pnpm repo:check
pnpm test
```

프로젝트 삭제 API는 DB에 연결된 파일만 정리하며, 처리 중인 작업이 있으면 삭제를 거부합니다.

## 운영 경계

현재 버전에는 로그인·사용자별 프로젝트 소유권 검사가 없습니다. 소규모 비공개 베타 이후 공개하기 전 인증과 권한 검사를 추가해야 합니다.
