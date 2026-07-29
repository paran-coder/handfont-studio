# HandFont Studio v3.3.1 Context Notes

## 목표
- v3.2.0 배포형 모노레포를 GitHub 최초 Push와 Vercel Import 직전 상태로 만든다.
- 저장소에 비밀정보, 사용자 업로드, 폰트 바이너리, 런타임 산출물이 들어가지 않도록 자동 검사한다.
- Vercel Development·Preview·Production 환경별 변수를 명확히 분리한다.
- 최초 DB 마이그레이션, 웹 배포, 워커 배포, 종단 스모크 테스트 순서를 재현 가능한 체크리스트로 제공한다.

## 유지할 구조
- `apps/web`: Next.js 웹·제어 API, Vercel 배포
- `workers/font-engine`: 독립 Docker 폰트 처리 워커
- `packages/contracts`: 웹·워커 공용 타입
- `infrastructure/migrations`: PostgreSQL 스키마
- `infrastructure/vercel`: Vercel 프로젝트 설정 참고 자료

## v3.3.1 추가 범위
- GitHub 최초 커밋·Push 자동화 스크립트
- 저장소 사전 검사와 환경변수 검사
- 랜덤 워커 공유 비밀 생성기
- GitHub Pull Request 템플릿, Dependabot, 보안 정책
- 브랜치 전략과 배포 체크리스트
- 환경별 변수 행렬과 Vercel 설정 순서
- 배포 후 스모크 테스트 절차

## 경계
- GitHub·Vercel 계정에 직접 로그인하거나 원격 저장소를 생성하지 않는다.
- 실제 DATABASE_URL, Blob 토큰, Queue 자격증명, 워커 URL을 소스에 기록하지 않는다.
- 외부 워커 공급자는 사용자가 선택한다.
- npm 레지스트리에 접근할 수 없는 실행 환경이므로 lockfile 생성과 실제 Next.js production build는 GitHub Actions에서 완료한다.

## v3.3.1 개인정보 정리
- 사용자 Flexcil 스크린샷 3장과 파생된 보정 페이지·글리프 검수표·폰트 미리보기를 제거한다.
- HTML 미리보기의 사용자 손글씨 SVG 105개를 합성 시스템 글리프로 교체한다.
- 알려진 원본·파생 파일 SHA-256과 민감 문자열을 Git Push 전 자동 검사한다.
- Queue/API 메시지 schemaVersion은 호환성을 위해 3.3.0을 유지한다.
