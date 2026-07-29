# HandFont Studio v3.3.1 Checklist

## 기본 문서
- [x] context-notes.md 갱신
- [x] checklist.md 갱신
- [x] README.md 갱신
- [x] User manual.md 갱신

## GitHub 최초 커밋
- [x] 저장소 사전 검사 스크립트
- [x] 워커 공유 비밀 생성기
- [x] 최초 커밋·원격 Push 스크립트
- [x] Pull Request 템플릿
- [x] Dependabot 설정
- [x] SECURITY.md와 CONTRIBUTING.md
- [x] CI 최소 권한·동시 실행 제어
- [x] 폰트·런타임·비밀정보 유입 검사

## Vercel 배포 준비
- [x] Development·Preview·Production 변수 행렬
- [x] Vercel 프로젝트 설정 참고 파일
- [x] 환경변수 로컬 검증 스크립트
- [x] 모노레포 Root Directory 설정 절차
- [x] DB 마이그레이션 순서
- [x] Private Blob·Queue·워커 연결 순서
- [x] 배포 후 스모크 테스트 절차

## 검증
- [ ] pnpm lockfile 생성
- [ ] pnpm install --frozen-lockfile
- [ ] Next.js production build
- [x] Node 스크립트 문법 검사
- [x] Python 워커 테스트
- [x] 저장소 사전 검사
- [x] ZIP 내 금지 파일 검사

## 사용자가 계정에서 수행할 작업
- [ ] GitHub 빈 저장소 생성
- [ ] 최초 Push
- [ ] GitHub Push Protection 활성화
- [ ] Vercel GitHub 저장소 Import
- [ ] PostgreSQL 연결
- [ ] Private Blob 생성
- [ ] Queue 활성화
- [ ] 환경변수 입력
- [ ] 최초 DB 마이그레이션
- [ ] 외부 워커 배포
- [ ] Preview 스모크 테스트
- [ ] Production 승격

## v3.3.1 개인정보 정리
- [x] 원본 스크린샷 3장 제거
- [x] 사용자 파생 데모 이미지 제거
- [x] HTML의 사용자 손글씨 SVG 제거
- [x] 합성 익명 데모로 교체
- [x] 개인정보 사전 검사 스크립트 추가
- [ ] GitHub Push 직전 privacy:check 재실행

## v3.3.2 OG 메타데이터

- [x] 1200×630 PNG 생성
- [x] Open Graph 이미지 파일 규칙 적용
- [x] Twitter Card 이미지 파일 규칙 적용
- [x] OG/Twitter 제목과 설명 설정
- [x] 이미지 대체 텍스트 추가
