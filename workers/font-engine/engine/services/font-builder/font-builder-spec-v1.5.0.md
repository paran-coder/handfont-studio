# HandFont Font Builder 기술 명세 v1.5.0

## 1. 목적

v1.4.0이 생성한 SVG 이차 베지어 윤곽선을 TrueType `glyf` 윤곽선으로 변환하고, 1000 UPM 메트릭과 필수 OpenType 테이블을 결합해 설치 가능한 TTF를 생성한다.

## 2. 입력 계약

`glyph-manifest.json`의 각 글리프는 다음 값을 가져야 한다.

- 문자 1개와 일치하는 Unicode codepoint
- SVG 파일 경로
- v1.4.0 contour metadata JSON 경로
- 선택적 category와 cell ID

SVG는 단일 `<path>`에 `M`, `L`, `Q`, `Z` 명령을 사용하며, metadata의 contour 순서와 SVG subpath 순서가 같아야 한다.

## 3. 좌표 정규화

- UPM: 1000
- ascender: 800
- descender: -200
- line gap: 200
- cap height: 700
- x-height: 500
- SVG Y축은 아래 방향이므로 TrueType 좌표 변환 시 반전한다.
- 수직 스케일을 우선 적용하며, 윤곽선 폭이 em-square 안전 영역을 넘으면 균일 축소한다.

## 4. 수직 배치 규칙

- 대문자·숫자: baseline 0, top 700
- 일반 소문자: baseline 0, top 500
- ascender 소문자 `bdfhklt`: top 700
- descender 소문자 `gjpqy`: bottom -200, top 500
- 구두점·수학 기호·괄호·통화 기호: 문자별 규칙표 적용

이 규칙은 이번 PoC의 자동 기준이며, 실제 필기 템플릿의 기준선 좌표가 연결되면 입력 기반 메트릭으로 교체한다.

## 5. 수평 메트릭

- 기본 LSB/RSB: 60/60 units
- 좁은 문자: 45/45 units
- 넓은 문자: 55/55 units
- 최소 advance width: 문자군별 220~520 units
- advance width는 10-unit 단위로 올림한다.
- `xMin == LSB`, `advance - xMax >= 0`을 빌드 후 검증한다.

## 6. 윤곽선 변환

1. SVG path를 contour별 RecordingPen으로 분리한다.
2. metadata의 `is_hole`을 읽는다.
3. 좌표 변환 후 signed area를 계산한다.
4. 외곽선은 양의 방향, 구멍은 음의 방향이 되도록 contour를 반전한다.
5. 좌표를 정수로 반올림하고 TTGlyphPen으로 `glyf` 글리프를 생성한다.

## 7. 생성 테이블

- `glyf`, `loca`, `maxp`
- `cmap`
- `hmtx`, `hhea`
- `head`
- `name`
- `OS/2`
- `post`
- 호환용 dummy `DSIG`

`OS/2`에는 cap height, x-height, typo/win 메트릭, Latin code page bit를 기록한다.

## 8. 출력

- TTF
- 글리프별 메트릭 CSV
- 전체 빌드 보고서 JSON
- SHA-256
- fontTools·fc-scan·Pillow 검증 JSON
- 문장 specimen PNG
- 전체 글리프 grid PNG

배포 패키지에는 실행 결과 TTF를 포함하지 않으며, 소스 코드와 입력 manifest로 동일 결과를 재생성할 수 있다.

## 9. 완료 기준

- UPM 1000
- 입력 88자 전부 빌드
- space 포함 cmap 89개
- 필수 테이블 누락 0개
- 빈 outline 0개
- 메트릭 위반 0개
- checksum 검증 성공
- fontTools, fc-scan, Pillow 로드 성공
- 동일 입력의 반복 빌드 SHA-256 일치
