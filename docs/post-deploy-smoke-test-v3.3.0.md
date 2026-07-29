# 배포 후 스모크 테스트

## 웹 기본

- [ ] 홈 화면 200 응답
- [ ] 프로젝트 생성 성공
- [ ] 새로고침 후 프로젝트 유지
- [ ] 브라우저 콘솔 오류 없음
- [ ] 모바일 너비에서 가로 넘침 없음

## 업로드

- [ ] PNG 업로드 성공
- [ ] PDF 업로드 성공
- [ ] 허용하지 않는 MIME 차단
- [ ] 크기 제한 초과 차단
- [ ] 업로드 URL이 Private Blob인지 확인
- [ ] 비인가 직접 URL 접근 차단

## 분석

- [ ] 분석 작업 DB 생성
- [ ] Queue 메시지 발행
- [ ] 워커 작업 수신
- [ ] 진행률 증가
- [ ] SVG 글리프 반영
- [ ] 실패 작업 오류 메시지 표시

## 내보내기

- [ ] 검수된 글리프로 내보내기 작업 생성
- [ ] 내부 TTF 검증 통과
- [ ] 결과 ZIP Private Blob 저장
- [ ] 권한 확인 후 다운로드
- [ ] 임시 파일 삭제

## 분리 검증

- [ ] Preview 작업이 Production DB에 없음
- [ ] Preview Blob이 Production 토큰으로 접근되지 않음
- [ ] Preview 워커가 Production topic을 소비하지 않음
- [ ] Preview와 Production 공유 비밀이 다름

## 완료 기록

- Commit SHA:
- Preview URL:
- Worker image digest:
- DB migration version:
- 테스트 시간:
- 담당자:
