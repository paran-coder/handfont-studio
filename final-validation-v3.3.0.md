# HandFont Studio v3.3.0 최종 검증

## 완료

- GitHub 최초 Push 스크립트와 dry-run 검증
- 저장소 비밀·폰트·DB·런타임 사전 검사
- Preview·Production 환경변수 분리
- Vercel monorepo 설정 참고 자료
- GitHub PR 템플릿, Dependabot, CI 최소 권한
- 배포 단계별 체크리스트
- 워커 배포와 종단 스모크 테스트 문서
- Vercel 시스템 URL 자동 감지
- schemaVersion 3.3.0 통일

## 자동 검증

- 배포 관련 테스트: 62/62 통과
- 저장소 사전 검사: 통과
- 최초 커밋 생성 dry-run: 통과
- 환경변수 검사: 통과
- Python·Node·TypeScript 정적 검사: 통과
- 폰트 바이너리: 0개
- DB·런타임 산출물: 0개

## 미완료

- `pnpm-lock.yaml` 생성
- 실제 Next.js production build
- GitHub 원격 저장소 Push
- Vercel 리소스 프로비저닝
- 외부 워커 배포
- Preview·Production 종단 검증

npm 레지스트리 DNS 접근이 불가능해 lockfile과 production build는 계정 배포 환경에서 완료해야 합니다.

## 배포 판정

**조건부 GitHub Push 준비 완료**입니다. 먼저 네트워크가 가능한 환경에서 `pnpm install`을 실행해 `pnpm-lock.yaml`을 생성하고 `node scripts/repo-preflight.mjs`를 다시 통과시킨 뒤 Push하십시오.
