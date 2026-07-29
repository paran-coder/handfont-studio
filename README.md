# HandFont Studio v3.3.1

손글씨 작성본을 업로드해 SVG 글리프와 TTF 폰트로 변환하는 **GitHub·Vercel 최초 배포 준비형 모노레포**입니다.

## 구성

- `apps/web`: Next.js App Router 웹 UI와 제어 API
- `workers/font-engine`: 독립 Docker Python 폰트 워커
- `packages/contracts`: 웹·워커 공용 계약
- `infrastructure/migrations`: PostgreSQL 마이그레이션
- `infrastructure/vercel`: Vercel 설정 참고 자료
- `scripts`: 저장소·환경변수·최초 Push 사전 검사
- `docs`: GitHub, Vercel, 워커, 보안, 스모크 테스트 문서

## 최초 실행

```bash
cp .env.example .env
node scripts/generate-worker-secret.mjs
# 출력된 값을 .env의 WORKER_SHARED_SECRET에 입력

docker compose -f infrastructure/docker-compose.local.yml up -d postgres
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

## GitHub 최초 Push

```bash
node scripts/repo-preflight.mjs
bash scripts/first-commit.sh https://github.com/<owner>/<repo>.git
```

원격 저장소가 이미 연결되어 있으면 URL 없이 실행할 수 있습니다.

```bash
bash scripts/first-commit.sh
```

상세 순서는 `docs/github-first-push-v3.3.1.md`를 따릅니다.

## Vercel 배포

Vercel 프로젝트의 Root Directory를 `apps/web`으로 지정하고, **Root Directory 밖의 소스 포함 옵션**을 활성화합니다. 이후 PostgreSQL, Private Blob, Queue를 연결하고 환경변수를 Development → Preview → Production 순서로 입력합니다.

- 배포 체크리스트: `docs/deployment-checklist-v3.3.1.md`
- 환경변수 행렬: `docs/environment-variables-v3.3.1.md`
- Vercel 절차: `docs/vercel-deployment-v3.3.1.md`
- 워커 절차: `docs/worker-deployment-v3.3.1.md`

## 안전장치

```bash
node scripts/repo-preflight.mjs
node scripts/check-env.mjs .env
```

사전 검사는 비밀정보 후보, 폰트 바이너리, 사용자 런타임 파일, 버전 불일치와 필수 배포 파일 누락을 검사합니다.


## 개인정보 안전 패치

- 사용자 업로드 원본과 그 파생 이미지·SVG를 저장소에서 제거했습니다.
- 브라우저 미리보기는 사용자 데이터와 무관한 합성 글리프만 사용합니다.
- `node scripts/privacy-preflight.mjs`가 알려진 샘플 해시, 원본 파일명, Base64 글리프 임베딩과 공개 데모 폴더의 사용자 산출물을 검사합니다.
- GitHub Push 전 `pnpm privacy:check`와 `pnpm repo:check`를 모두 실행해야 합니다.

## 운영 경계

- v3.3.1에는 로그인·결제·사용자별 프로젝트 소유권 격리가 없습니다.
- 최초 공개는 Vercel Deployment Protection을 적용한 비공개 베타가 적합합니다.
- OpenCV·PDF·SVG·TTF 처리는 독립 워커에서 수행합니다.
- 실제 비밀값은 `.env`나 Vercel·워커 환경변수에만 저장하고 Git에 커밋하지 않습니다.
