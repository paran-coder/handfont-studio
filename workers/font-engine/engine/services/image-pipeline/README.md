# HandFont Image Pipeline v1.3.0

HandFont Studio 작성지를 촬영하거나 스캔한 이미지에서 등록 마커를 찾고, 페이지를 A4 기준 좌표계로 원근 보정한 뒤 5x7 작성 칸과 필기 잉크를 분리하는 Python PoC입니다.

## 구현 범위

- PNG, JPEG, WEBP, TIFF, BMP 입력
- PDF 단일 페이지 렌더링 입력
- 네 모서리 검정 등록 마커 검출
- 등록 마커 중심점 기반 호모그래피 원근 보정
- 150/200/300/400 dpi A4 출력
- 5열 x 7행, 35칸 고정 레이아웃 추출
- 문자, 유니코드, 페이지, 칸 ID 매핑
- 빈 템플릿 배경 차감 기반 필기 잉크 마스크
- 누락, 희박, 정상, 과밀 상태 분류
- 원본 칸, 작성 영역, 잉크 마스크, 디버그 오버레이 저장
- JSON 메타데이터 출력

## 설치

```bash
cd services/image-pipeline
python -m pip install -r requirements.txt
```

## 이미지 처리

```bash
PYTHONPATH=. python -m handfont_pipeline.cli process \
  --input my-photo.jpg \
  --template-page 1 \
  --output output/page-01 \
  --dpi 300
```

## PDF 처리

작성지 1페이지는 전체 템플릿 PDF의 2페이지에 해당합니다.

```bash
PYTHONPATH=. python -m handfont_pipeline.cli process \
  --input ../../handfont-writing-template-v1.3.0.pdf \
  --pdf-page 2 \
  --template-page 1 \
  --output output/pdf-page-01 \
  --dpi 300
```

## 결과 구조

```text
output/page-01/
├─ marker-debug.png
├─ rectified.png
├─ overlay.png
├─ metadata.json
└─ cells/
   ├─ P01-C01/
   │  ├─ cell.png
   │  ├─ writing.png
   │  ├─ ink-mask.png
   │  └─ ink.png
   └─ ...
```

## 테스트

```bash
PYTHONPATH=. pytest
```

## 합성 벤치마크

```bash
PYTHONPATH=. python scripts/benchmark.py \
  --output examples/benchmark-v1.3.0 \
  --dpi 150 \
  --seed 20260728
```

현재 벤치마크는 9개 작성 페이지와 6개 촬영 조건을 조합한 54건입니다. 실제 프린터와 스마트폰으로 만든 촬영 데이터는 다음 검증 단계에 포함해야 합니다.
