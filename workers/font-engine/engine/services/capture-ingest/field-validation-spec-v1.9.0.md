# HandFont Studio 현장 촬영 검증 명세 v1.9.0

## 1. 목적
실제 스마트폰 촬영본이 폰트 글리프 추출에 적합한지 셀 처리 전에 판정하고, 품질 결함을 구체적인 재촬영 행동으로 변환한다.

## 2. 입력
- PNG, JPEG, WEBP, TIFF
- 작성지 페이지 1~9
- 선택 사항: 자동 등록 마커 검출 실패 시 사용할 수동 모서리 JSON
- 데이터 출처: `real` 또는 `synthetic`

## 3. 측정 지표
| 지표 | 의미 | 기본 판정 방향 |
|---|---|---|
| megapixels | 입력 이미지 실제 픽셀 수 | 낮을수록 불리 |
| sharpness | 라플라시안 기반 선명도 | 낮을수록 불리 |
| exposure | 종이 명도와 잉크 대비 | 낮을수록 불리 |
| glare | 국소 과노출 반사 영역 비율 | 높을수록 불리 |
| shadow | 저주파 조명 불균일 | 높을수록 불리 |
| perspective | 사각형 변형 정도 | 높을수록 불리 |
| page_coverage | 페이지가 사진을 차지하는 비율 | 낮을수록 불리 |
| marker_confidence | 등록 마커 검출 신뢰도 | 낮을수록 불리 |
| page_confidence | 페이지 식별 신뢰도 | 낮을수록 불리 |

## 4. 기본 임계값
`balanced` 프로필의 기본값이다. 실데이터 수집 후 기기군별 재교정할 수 있다.

- 해상도: 통과 2.0MP 이상, 재촬영 1.15MP 미만
- 선명도: 통과 0.25 이상, 재촬영 0.13 미만
- 노출: 통과 0.68 이상, 재촬영 0.46 미만
- 반사광: 통과 0.050 이하, 재촬영 0.085 초과
- 그림자: 통과 0.14 이하, 재촬영 0.29 초과
- 원근: 통과 0.15 이하, 재촬영 0.30 초과
- 페이지 점유율: 통과 0.52 이상, 재촬영 0.38 미만
- 페이지 식별: 0.30 미만이면 처리 불가

## 5. 상태
- `accept`: 자동 처리 가능
- `review`: 자동 처리는 가능하지만 결과 검수 필요
- `retake`: 글리프 품질 손실 가능성이 높아 재촬영 권장
- `blocked`: 마커·페이지 식별 실패 또는 누락 페이지로 처리 불가

중복 페이지는 상태가 더 양호하고 품질 점수가 높은 촬영본을 선택한다. 선택되지 않은 저품질 중복 사진이 `retake`여도 세션 전체를 불필요하게 차단하지 않는다.

## 6. 출력
- `preflight-report.json`: 전체 판정과 임계값
- `photo-results.csv`: 사진별 측정값
- `retake-list.csv`: 재촬영·누락 페이지 목록
- `preflight-report.html`: 브라우저 검수 보고서
- `preflight-overview.png`: 사진별 상태 썸네일

## 7. CLI
```bash
python -m handfont_capture preflight \
  --input ./photos \
  --output ./preflight-result \
  --manual-corners ./manual-corners.json \
  --data-origin real
```

## 8. 데이터 진실성
`data_origin=synthetic` 결과는 알고리즘 교정용이며 실제 사용자 성공률로 해석하지 않는다. 실사진 결과는 별도 세션 ID와 `data_origin=real`로 저장한다.
