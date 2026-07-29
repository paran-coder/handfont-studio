# Contributing

## 브랜치

- `main`: Production 배포 대상
- `develop`: 통합 Preview
- `feat/*`, `fix/*`, `chore/*`: 작업 브랜치

## 변경 절차

1. 작업 브랜치를 만듭니다.
2. `node scripts/repo-preflight.mjs`를 실행합니다.
3. 웹·워커 테스트를 실행합니다.
4. Pull Request 템플릿을 작성합니다.
5. Preview 배포에서 업로드·분석·내보내기 흐름을 확인합니다.
6. CI와 리뷰가 통과한 뒤 병합합니다.

## 금지 사항

- 실제 토큰과 DATABASE_URL 커밋
- 사용자 작성본과 생성 폰트 커밋
- 테스트를 우회하기 위한 예외 처리
- Preview에서 확인하지 않은 직접 Production Push
