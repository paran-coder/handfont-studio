# HandFont Orchestrator 기술 명세 v2.0.0

## 1. 목적
분리된 촬영 검사, 이미지 처리, 벡터화, 한글 조합, 폰트 빌드 서비스를 하나의 재현 가능한 실행 흐름으로 묶는다.

## 2. 단계
1. `preflight`: 사진 품질과 페이지 1~9 완전성 검사
2. `capture-ingest`: 페이지 선택, 원근 보정, 315개 셀 추출, 잉크 마스크 및 SVG 생성
3. `captured-manifest`: 직접 작성·벡터화된 문자의 폰트 manifest 생성
4. `representative-masks`: 한글 대표 음절 168개를 480×480 기준 좌표로 정규화
5. `hangul-composition`: 작성하지 않은 음절을 위치형 템플릿으로 조합·벡터화
6. `font-build-validation`: 직접 글리프와 조합 글리프를 병합해 내부 TTF 생성, 테이블·메트릭·렌더링 검사 후 삭제

## 3. 상태 정책
- `accept`: 계속
- `review`: 경고 기록 후 계속
- `retake`: 기본 중단, `--allow-retake`에서만 계속
- `blocked`: 항상 중단

## 4. 재실행
`--resume`은 완료된 단계의 JSON 결과를 사용한다. `run-request.json`의 입력 파일 SHA-256, 수동 모서리 파일 SHA-256, 실행 옵션이 기존 요청과 동일할 때만 허용한다. 옵션이나 입력이 다르면 새 출력 폴더를 요구한다.

## 5. 좌표 정규화
촬영 셀의 잉크 마스크 크기는 작성 ROI에 따라 달라진다. 한글 조합기는 480×480 기준 위치 영역을 사용하므로 다음 변환을 적용한다.

1. 마스크 전경 경계 상자 추출
2. 해당 대표 음절의 `glyph_ink_bbox` 안에 종횡비를 유지해 맞춤
3. 480×480 검정 캔버스에 중앙 배치
4. 이진화 후 `U+XXXX.png`로 저장

이 변환은 좌표계 불일치를 해결하지만 실제 획 단위 자모 분리를 대신하지는 않는다.

## 6. 폰트 보안 정책
TTF·OTF·WOFF·WOFF2는 통합 검증 과정에서만 임시 생성한다. 체크섬, Fontconfig, Pillow, cmap, 윤곽선, 메트릭 검증 후 바이너리를 삭제한다. 배포물에는 SHA-256과 PNG 렌더링 결과만 남긴다.

## 7. 주요 출력
- `run-request.json`: 입력·옵션 지문
- `run-report.json`: 전체 실행 결과
- `run-report.normalized.json`: 시간·캐시 상태를 제거한 의미 기반 보고서
- `run-report.html`: 브라우저 검수 화면
- 단계별 JSON·CSV·PNG·SVG
