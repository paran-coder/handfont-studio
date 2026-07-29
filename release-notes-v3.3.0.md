# HandFont Studio v3.3.0 Release Notes

## 추가

- GitHub 최초 커밋·Push 자동화
- 저장소 비밀정보·폰트·런타임 사전 검사
- Preview·Production 환경변수 분리 템플릿
- Vercel 프로젝트 설정 참고 파일
- GitHub Pull Request 템플릿과 Dependabot
- 배포·스모크 테스트 체크리스트
- Vercel 시스템 URL 자동 감지

## 변경

- CI에 최소 권한과 중복 실행 취소 적용
- CI 설치를 `pnpm install --frozen-lockfile`로 강화
- 패키지 버전을 3.3.0으로 통일

## 남은 계정 작업

- pnpm lockfile 생성
- GitHub 최초 Push
- Vercel Preview 리소스 프로비저닝
- 외부 워커 배포
- Production 승격
