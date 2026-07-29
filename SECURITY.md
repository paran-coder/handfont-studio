# Security Policy

## 지원 버전

현재 보안 수정 대상은 최신 `main` 브랜치와 v3.3.x입니다.

## 취약점 제보

공개 Issue에 토큰, 데이터베이스 URL, 사용자 업로드 또는 재현 가능한 공격 자격증명을 올리지 마십시오. 저장소 소유자에게 비공개 채널로 다음 내용을 전달하십시오.

- 영향받는 버전과 경로
- 재현 단계
- 예상 영향
- 가능한 완화책

## 저장소 보안 원칙

- 실제 `.env` 파일은 커밋하지 않습니다.
- 사용자 입력, TTF·OTF·WOFF, DB 파일과 런타임 산출물은 Git에서 제외합니다.
- Preview와 Production의 DB·Blob·Queue·공유 비밀을 분리합니다.
- GitHub Push Protection과 Secret Scanning을 활성화합니다.
- 비밀값 변경 후에는 Vercel과 워커를 모두 재배포합니다.
