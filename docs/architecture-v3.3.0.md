# v3.3.0 배포 아키텍처

## 제어 계층

- Next.js App Router가 Vercel에서 실행됩니다.
- 프로젝트·업로드·글리프·작업 상태는 PostgreSQL에 저장합니다.
- 브라우저는 Private Blob으로 직접 업로드합니다.
- 웹은 Queue에 작은 작업 메시지만 발행합니다.

## 처리 계층

- 독립 Docker 워커가 Queue 메시지를 소비합니다.
- 워커는 Private Blob에서 입력을 내려받습니다.
- 이미지 보정, 셀 추출, SVG 벡터화와 TTF 빌드를 수행합니다.
- 진행률과 결과를 서명된 내부 API로 웹에 기록합니다.
- 산출물은 Private Blob에 저장합니다.

## 환경 격리

Development, Preview, Production은 다음 항목을 분리합니다.

- PostgreSQL 데이터베이스
- Blob store 또는 token
- Queue topic
- 워커 공유 비밀
- 워커 consumer group

## Git 흐름

- 기능 브랜치 Push와 Pull Request: Vercel Preview
- `develop`: 통합 Preview
- `main`: Production
- CI 통과 전 병합 금지

## 보안 경계

- 실제 비밀값은 Git에 저장하지 않습니다.
- 사용자 작성본과 폰트 바이너리는 Git·배포 소스에서 제외합니다.
- Blob 다운로드는 프로젝트 권한 검증 API를 통합니다.
- 워커 콜백은 timing-safe shared secret 검사 후 처리합니다.
