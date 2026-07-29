# HandFont Orchestrator v2.0.0

분리된 6개 서비스를 단일 실행 흐름으로 연결합니다.

```bash
python -m handfont_orchestrator run \
  --input /path/to/photos \
  --output /path/to/output \
  --data-origin real \
  --family-name "My Handwriting"
```

## 중단 정책
- `blocked`: 즉시 중단
- `retake`: 기본 중단
- `review`: 경고를 기록하고 계속
- `--allow-retake`: 개발·긴급 검증 시에만 재촬영 권장 상태를 통과

## 보안 및 배포
내부 TTF는 검증 직후 삭제합니다. `--keep-intermediate-font`는 로컬 디버깅 전용이며 배포 패키지에는 폰트 파일을 포함하지 않습니다.
