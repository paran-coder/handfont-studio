# HandFont Studio v3.3.1 Release Notes

## 개인정보 안전 패치

- 사용자 Flexcil 원본 스크린샷 3장을 저장소·배포 패키지에서 제거했습니다.
- 사용자 작성본에서 파생된 보정 페이지, 글리프 검수표와 폰트 미리보기를 제거했습니다.
- HTML 미리보기에 포함되어 있던 사용자 손글씨 SVG 105개를 합성 익명 데모로 교체했습니다.
- `scripts/privacy-preflight.mjs`를 추가해 알려진 원본·파생 SHA-256, 민감 파일명, Base64 SVG 임베딩과 공개 데모 산출물을 검사합니다.
- `scripts/first-commit.sh`가 Git 커밋 전에 개인정보 검사와 저장소 검사를 모두 실행하도록 강화했습니다.

## 호환성

- 애플리케이션 패키지 버전은 3.3.1입니다.
- Queue/API 메시지 `schemaVersion`은 v3.3.0 워커와의 호환성을 위해 3.3.0을 유지합니다.
