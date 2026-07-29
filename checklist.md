# HandFont Studio v3.3.6 Checklist

## 기본 문서
- [x] context-notes.md 갱신
- [x] checklist.md 갱신
- [x] README.md 갱신
- [x] User manual.md 갱신

## 익명 소유권
- [x] 첫 방문 소유자 쿠키 발급
- [x] 원문 쿠키 대신 SHA-256 소유자 ID 저장
- [x] 프로젝트 생성과 목록을 소유자별로 제한
- [x] 프로젝트 상세·검수 페이지 소유권 검사
- [x] 프로젝트 조회·삭제 API 소유권 검사
- [x] 작업 생성·상태 조회 API 소유권 검사
- [x] 로컬·Blob 업로드 소유권 검사
- [x] 비공개 Blob 프록시 소유권 검사
- [x] 다른 소유자 접근 시 404 응답
- [x] 기존 워커 내부 API 호환성 유지

## 데이터베이스
- [x] owner_id 기본값 제거 마이그레이션 제공
- [x] owner_id + updated_at 인덱스 마이그레이션 제공
- [x] 기존 anonymous 프로젝트 자동 이전 금지

## 사용자 안내
- [x] 브라우저별 저장 안내 표시
- [x] 쿠키 삭제 시 복구 불가 안내
- [x] 다른 기기 동기화는 로그인 기능 이후 제공 안내

## 검증
- [x] TypeScript 엄격 구문·계약 검사
- [ ] Next.js production build
- [x] 웹 계약 테스트
- [x] Python 워커 테스트
- [x] Python 컴파일 검사
- [x] Node.js 문법 검사
- [x] 개인정보 사전 검사
- [x] 저장소 사전 검사
- [x] 핫픽스 ZIP 경로 검사
- [x] 전체·핫픽스 ZIP 무결성 검사

## 미실행 사유
- npm 레지스트리 DNS 접근이 불가능하여 실제 의존성 설치와 `next build`는 실행하지 못함
