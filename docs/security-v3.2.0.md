# 보안 기준

- 업로드는 Private Blob을 사용합니다. 브라우저 미리보기와 다운로드는 소유 프로젝트를 확인하는 `/api/blob` 스트리밍 경로를 거칩니다.
- 웹 서버를 경유하지 않는 client upload로 대용량 요청 제한을 회피합니다.
- 워커 내부 API는 `x-handfont-worker-secret`을 timing-safe 방식으로 확인합니다.
- 허용 MIME은 JPEG, PNG, WEBP, PDF로 제한합니다.
- 파일당 기본 최대 크기는 25MB입니다.
- 사용자 업로드·TTF·OTF·WOFF 파일은 Git 저장소와 배포 소스에 포함하지 않습니다.
- 운영 전 사용자 인증과 프로젝트 소유권 검사를 추가해야 합니다.
