# HandFont Studio v3.3.6 Release Notes

## Added
- 브라우저별 익명 소유권 쿠키
- SHA-256 기반 owner_id 저장
- 프로젝트·업로드·작업·Blob 전 구간 소유권 검사
- 소유권 안내 UI
- owner_id 조회 인덱스 마이그레이션

## Security
- 다른 브라우저의 프로젝트 목록·상세·삭제·파일 다운로드 차단
- 소유하지 않은 자원은 404로 응답해 존재 여부 비공개
- 원문 브라우저 토큰 DB 저장 금지

## Compatibility
- 워커 내부 API와 Queue schemaVersion 3.3.0 유지
- 기존 anonymous 프로젝트는 자동 이전하지 않음
