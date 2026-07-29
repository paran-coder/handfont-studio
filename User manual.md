# HandFont Studio v3.3.1 사용자 매뉴얼

## 서비스 이용 흐름

1. 새 프로젝트를 만들고 폰트 이름을 입력합니다.
2. JPG·PNG·WEBP·PDF 작성본을 선택합니다.
3. 브라우저가 Private Blob으로 파일을 직접 업로드합니다.
4. `작성본 분석 시작`을 누릅니다.
5. 워커가 페이지 보정, 셀 추출과 SVG 벡터화를 수행합니다.
6. 글리프 검수 화면에서 결과를 확인하고 상태를 수정합니다.
7. 스타일 설정을 저장한 뒤 `TTF 패키지 생성`을 누릅니다.
8. 폰트 검증이 끝나면 비공개 다운로드 경로에서 결과를 받습니다.

## 배포 담당자 순서

1. `node scripts/repo-preflight.mjs`를 실행합니다.
2. GitHub 빈 저장소를 만들고 `scripts/first-commit.sh`로 Push합니다.
3. GitHub Push Protection을 활성화합니다.
4. Vercel에서 저장소를 Import합니다.
5. PostgreSQL·Private Blob·Queue를 연결합니다.
6. `docs/environment-variables-v3.3.1.md` 순서대로 환경변수를 입력합니다.
7. Preview 배포 후 DB 마이그레이션과 스모크 테스트를 수행합니다.
8. 외부 Docker 워커를 배포하고 동일한 공유 비밀과 Blob·Queue 설정을 입력합니다.
9. Preview에서 종단 처리에 성공한 뒤 Production으로 승격합니다.

초기 배포에서는 접근 권한이 없는 사용자가 작성본과 결과 파일에 접근하지 못하도록 Deployment Protection을 유지합니다.

## 저장소 공개 전 개인정보 확인

```bash
pnpm privacy:check
pnpm repo:check
```

두 검사가 모두 통과하기 전에는 GitHub에 Push하지 않습니다.
