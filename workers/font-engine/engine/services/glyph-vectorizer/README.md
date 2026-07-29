# HandFont Glyph Vectorizer v1.4.0

HandFont Studio 이미지 파이프라인이 만든 `ink-mask.png`를 SVG 윤곽선으로 변환하는 Python PoC입니다. 외곽선과 내부 구멍을 계층적으로 추출하고, 노드를 단순화한 뒤 코너를 보존하는 이차 베지어 경로를 생성합니다. 목표 IoU에 미달하면 단순화 강도를 자동으로 완화해 최대 3회 다시 계산합니다.

## 설치

```bash
cd services/glyph-vectorizer
python -m pip install -r requirements.txt
```

## 단일 마스크 변환

```bash
PYTHONPATH=. python -m handfont_vectorizer.cli vectorize \
  --input ../image-pipeline/examples/synthetic-page-01/cells/P01-C01/ink-mask.png \
  --output output/P01-C01 \
  --title "가"
```

## 이미지 파이프라인 결과 일괄 변환

```bash
PYTHONPATH=. python -m handfont_vectorizer.cli batch \
  --input-dir ../image-pipeline/examples/synthetic-page-01/cells \
  --output output/synthetic-page-01
```

전경이 없는 빈 칸은 `skipped`, 실제 처리 오류는 `failed`로 분리되며 `batch-summary.json`에서 확인할 수 있습니다.

## 결과 구조

```text
output/P01-C01/
├─ glyph.svg
├─ metadata.json
├─ original-mask.png
├─ vector-raster.png
├─ difference.png
└─ overlay.png
```

`difference.png`에서 짙은 회색은 일치 영역, 파란색은 원본에만 있는 영역, 주황색은 벡터 결과에만 추가된 영역입니다.

## 테스트

```bash
PYTHONPATH=. pytest
```

## 대표 문자 벤치마크

```bash
PYTHONPATH=. python scripts/benchmark.py \
  --output examples/benchmark-v1.4.0
```

## 검증 결과

- 자동 테스트: 17/17 통과
- 대표 문자 최소 IoU: 0.9029
- 대표 문자 평균 IoU: 0.9423
- 대표 문자 평균 노드 감소율: 80.5%
- v1.3.0 연동: 필기 8개 성공, 빈 칸 27개 건너뜀, 실패 0개
