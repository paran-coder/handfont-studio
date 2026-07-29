# HandFont Capture Ingest v1.9.0

촬영본 페이지 식별·원근 보정·셀 추출과 현장 품질 preflight를 제공한다.

## 설치
```bash
pip install -r requirements.txt
```

## 현장 품질 검사
```bash
PYTHONPATH=.:../image-pipeline:../glyph-vectorizer:../hangul-engine \
python -m handfont_capture preflight \
  --input ./photos \
  --output ./preflight-result \
  --data-origin real
```

## 전체 수집 처리
```bash
PYTHONPATH=.:../image-pipeline:../glyph-vectorizer:../hangul-engine \
python -m handfont_capture ingest \
  --input ./photos \
  --output ./processed \
  --manual-corners ./manual-corners.json
```

## 합성 현장 벤치마크
```bash
PYTHONPATH=.:../image-pipeline:../glyph-vectorizer:../hangul-engine \
python -m handfont_capture field-benchmark \
  --output ./field-benchmark \
  --count-per-class 8
```

실제 촬영 결과는 `--data-origin real`, 합성 검증은 `--data-origin synthetic`을 사용한다.
