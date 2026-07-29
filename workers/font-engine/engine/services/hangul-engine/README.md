# HandFont Hangul Engine v1.6.0

한글 대표 음절 168자를 유니코드 자모로 분해하고, 글자 구조에 맞는 위치형 데이터를 생성한 뒤 기존 벡터화·TTF 빌드 서비스로 연결하는 PoC입니다.

## 처리 흐름

```text
character-set-v1.3.0.csv
→ 대표 음절 168자 선택
→ 합성 검증 마스크 생성
→ 초성·중성·종성 유니코드 분해
→ 세로·가로·복합 모음 및 받침 유무 분류
→ 위치 영역·position form ID 생성
→ SVG 벡터화
→ 1000 UPM 한글 고정폭 TTF 내부 빌드
→ cmap·OS/2·메트릭·렌더링 검증
```

## 데이터 생성

```bash
cd services/hangul-engine
PYTHONPATH=. python -m handfont_hangul.cli \
  --output examples/hangul-source-v1.6.0 \
  --charset ../../character-set-v1.3.0.csv \
  --vectorizer-root ../glyph-vectorizer
```

## 내부 TTF 검증 빌드

```bash
cd services/font-builder
PYTHONPATH=. python -m handfont_fontbuilder.cli build \
  --manifest ../hangul-engine/examples/hangul-source-v1.6.0/hangul-glyph-manifest.json \
  --output ../hangul-engine/examples/hangul-font-v1.6.0 \
  --family-name "HandFont Studio Hangul PoC" \
  --output-basename "HandFontStudioHangulPoc-Regular"
```

배포 패키지에는 생성된 폰트 바이너리가 포함되지 않습니다. 코드와 입력 SVG, 빌드·검증 보고서, 렌더링 미리보기로 결과를 재현할 수 있습니다.

## 테스트

```bash
PYTHONPATH=. pytest
```

## 핵심 출력

- `hangul-glyph-manifest.json`: 168자 벡터 입력 매니페스트
- `hangul-position-map.json`: 음절별 자모·레이아웃·위치 영역
- `hangul-position-map.csv`: 분석용 평면 매핑
- `position-regions/U+XXXX/`: 역할별 위치 영역 마스크
- `validation-summary-v1.6.0.json`: 전체 품질·TTF 검증 요약
- `position-region-sheet.png`: 6개 레이아웃 시각 검수표
