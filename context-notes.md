# HandFont Studio v3.3.4 Context Notes

## 목표
- 배포된 웹앱에서 사용자가 빈 손글씨 작성 양식을 바로 내려받을 수 있게 한다.
- 생성한 프로젝트를 화면에서 삭제하고, 연결된 업로드·글리프·완성 폰트 파일까지 함께 정리한다.
- 완료된 TTF 패키지를 프로젝트를 다시 연 뒤에도 재다운로드할 수 있게 한다.

## 구현 범위
- `apps/web/public/templates`: 9페이지 작성 양식 PNG와 통합 PDF·PNG ZIP
- `apps/web/app/api/projects/[projectId]`: 프로젝트 조회와 삭제 API
- `apps/web/lib/repository.ts`: 최신 내보내기 결과 조회, 활성 작업 검사, 프로젝트 파일 목록·삭제
- `apps/web/components`: 작성 양식 다운로드와 프로젝트 삭제 UI
- 프로젝트 목록·상세 화면: 삭제 버튼, 완료 결과 재다운로드 버튼

## 삭제 정책
- 상태가 `queued`, `leased`, `running`인 작업이 있으면 프로젝트 삭제를 막는다.
- 로컬 저장소의 파일은 허용된 Blob 루트 아래에서만 삭제한다.
- Vercel Blob 파일은 프로젝트 DB에 연결된 URL만 삭제한다.
- 파일 정리가 성공한 뒤 PostgreSQL 프로젝트 행을 삭제하며, 하위 행은 외래키 cascade로 정리한다.

## 다운로드 정책
- 작성 양식은 사용자 데이터가 없는 정적 자산이다.
- PDF는 9페이지 A4 문서이며, PNG 묶음은 ZIP으로 제공한다.
- 완성 폰트는 가장 최근의 완료된 `export` 작업 중 `artifact_url`이 있는 결과를 표시한다.

## 운영 경계
- 현재 버전에는 사용자 로그인과 프로젝트 소유권 격리가 없다.
- 공개 서비스 전에는 인증·권한 검사를 추가해야 한다.
- Queue/API 메시지 `schemaVersion`은 기존 워커 호환성을 위해 `3.3.0`을 유지한다.
