# GitHub 최초 커밋·Push 절차

## 1. 로컬 사전 검사

```bash
node scripts/repo-preflight.mjs
```

`pnpm-lock.yaml` 경고가 나오면 네트워크가 가능한 컴퓨터에서 다음 명령을 먼저 실행합니다.

```bash
corepack enable
pnpm install
node scripts/repo-preflight.mjs
```

생성된 `pnpm-lock.yaml`은 반드시 최초 커밋에 포함합니다.

## 2. GitHub 빈 저장소 생성

- README, `.gitignore`, License를 GitHub에서 자동 생성하지 않습니다.
- 저장소 공개 범위는 초기에는 Private을 권장합니다.
- 기본 브랜치는 `main`으로 둡니다.

## 3. 최초 커밋과 Push

```bash
bash scripts/first-commit.sh https://github.com/<owner>/<repository>.git
```

스크립트는 다음을 수행합니다.

1. 저장소 사전 검사
2. `git init -b main`
3. 전체 파일 Stage
4. 최초 커밋 생성
5. `origin` 연결
6. `main` Push

직접 수행하려면 다음 명령을 사용합니다.

```bash
git init -b main
git add .
git commit -m "chore: prepare HandFont Studio v3.3.1 deployment"
git remote add origin https://github.com/<owner>/<repository>.git
git push -u origin main
```

## 4. GitHub 저장소 설정

`Settings → Code security and analysis`에서 다음 항목을 활성화합니다.

- Secret scanning
- Push protection
- Dependabot alerts
- Dependabot security updates

`Settings → Branches`에서 `main` 보호 규칙을 추가합니다.

- Pull Request 없이 직접 병합 금지
- CI 상태 검사 통과 요구
- 최소 1명 승인 권장
- Force push 금지
- 브랜치 삭제 금지

## 5. 템플릿 수정

`.github/ISSUE_TEMPLATE/config.yml`의 `OWNER/REPOSITORY`를 실제 저장소 주소로 바꿉니다.

## 6. 권장 브랜치

```text
main                 Production
develop              통합 Preview
feat/<name>           기능 개발
fix/<name>            버그 수정
chore/<name>          배포·문서·도구
```

## 완료 기준

- `main`에 최초 커밋 존재
- Actions CI가 실행됨
- 저장소에 실제 `.env`, 사용자 작성본, 폰트 바이너리가 없음
- Push protection 활성화
- `pnpm-lock.yaml` 포함

## 공식 참고 문서

- Push Protection: https://docs.github.com/en/code-security/concepts/secret-security/push-protection
- Secret Scanning: https://docs.github.com/code-security/secret-scanning/about-secret-scanning
