# GitHub·Vercel 실제 배포 체크리스트

## A. 저장소 준비

- [ ] 네트워크 가능한 환경에서 `pnpm install` 실행
- [ ] `pnpm-lock.yaml` 생성·커밋
- [ ] `node scripts/repo-preflight.mjs` 통과
- [ ] GitHub Private 저장소 생성
- [ ] `main` 최초 Push
- [ ] Push Protection 활성화
- [ ] Branch Protection 설정
- [ ] GitHub Actions CI 통과

## B. Vercel Preview 프로젝트

- [ ] GitHub 저장소 Import
- [ ] Framework: Next.js
- [ ] Root Directory: `apps/web`
- [ ] Root Directory 밖 소스 포함 활성화
- [ ] Node.js 22.x
- [ ] Install Command 확인
- [ ] Build Command 확인
- [ ] Production Branch: `main`
- [ ] Deployment Protection 활성화

## C. Preview 리소스

- [ ] Preview PostgreSQL 연결
- [ ] Preview Private Blob 생성
- [ ] Preview Queue 활성화
- [ ] Preview 환경변수 입력
- [ ] Preview DB 마이그레이션
- [ ] Preview 웹 배포 성공

## D. Preview 워커

- [ ] Docker 이미지 빌드
- [ ] 외부 워커 서비스 생성
- [ ] Preview 워커 환경변수 입력
- [ ] 최소 2 vCPU·2GB RAM 설정
- [ ] 동시 처리 1개로 시작
- [ ] 워커 Health/로그 확인

## E. Preview 종단 검증

- [ ] 프로젝트 생성
- [ ] 이미지 직접 업로드
- [ ] 작업 Queue 등록
- [ ] 워커 작업 수신
- [ ] SVG 글리프 생성
- [ ] 검수 화면 갱신
- [ ] TTF 내보내기
- [ ] Private 결과 다운로드
- [ ] 비인가 Blob 접근 차단
- [ ] 실패 작업 재시도 확인

## F. Production

- [ ] Preview와 분리된 DB 생성
- [ ] Preview와 분리된 Private Blob 생성
- [ ] Production Queue topic 설정
- [ ] Production 전용 공유 비밀 생성
- [ ] Production 환경변수 입력
- [ ] Production DB 마이그레이션
- [ ] Production 워커 배포
- [ ] Preview 배포를 Production으로 승격
- [ ] Production 스모크 테스트
- [ ] 도메인 연결
- [ ] 로그·알림·비용 한도 설정

## 중단 조건

다음 중 하나라도 발생하면 Production 승격을 중단합니다.

- CI 또는 production build 실패
- DB 마이그레이션 실패
- 사용자 업로드가 Public Blob으로 저장됨
- 워커와 웹의 공유 비밀 불일치
- 작업 완료 후 글리프가 프로젝트에 반영되지 않음
- TTF 검증 위반 발생
- 저장소 또는 배포 로그에 비밀값 노출
