# HandFont Font Builder v1.6.0

SVG 글리프와 contour metadata를 받아 1000 UPM TrueType 폰트로 변환하는 Python PoC입니다. v1.6.0부터 한글 1000-unit 고정폭과 OS/2 한글 범위를 지원합니다.

## 처리 흐름

```text
SVG + metadata
→ 문자 유형별 수직 메트릭 결정
→ 1000 UPM 좌표 변환과 Y축 반전
→ 외곽선·구멍 winding 정규화
→ 좌우 여백과 advance width 계산
→ glyf/cmap/name/OS/2 등 OpenType 테이블 생성
→ TTF 재로드, fc-scan, Pillow 렌더링 검증
```

## 설치

```bash
cd services/font-builder
python -m pip install -r requirements.txt
```

## PoC 입력 생성

실제 사용자 필기 데이터가 준비되지 않은 단계이므로, 프로젝트 문자 세트의 영문·숫자·기호 88자를 참조 글꼴로 래스터화하고 v1.4.0 벡터화기를 통과시킵니다.

```bash
PYTHONPATH=. python scripts/generate_poc_dataset.py \
  --output examples/poc-source-v1.5.0
```

## TTF 빌드

```bash
PYTHONPATH=. python -m handfont_fontbuilder.cli build \
  --manifest examples/poc-source-v1.5.0/glyph-manifest.json \
  --output examples/poc-font-v1.5.0 \
  --family-name "HandFont Studio PoC"
```

## 테스트

```bash
PYTHONPATH=. pytest
```

## 출력

- `HandFontStudioPoc-Regular.ttf`
- `font-build-report.json`
- `glyph-metrics.csv`
- `font-validation.json`
- `fc-scan.txt`
- `font-specimen.png`
- TTF SHA-256 파일


## v1.6.0 한글 확장

한글 대표 음절 manifest를 입력하면 각 음절을 1000-unit 고정폭으로 빌드하고 Hangul Unicode Range와 Korean Wansung CodePage를 설정합니다. 세부 규칙은 `font-builder-spec-v1.6.0.md`를 참조하십시오.
