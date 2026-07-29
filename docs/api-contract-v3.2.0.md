# 제어 API 계약

## 공개 API
- `GET /api/health`
- `GET|POST /api/projects`
- `GET /api/projects/:projectId`
- `GET /api/projects/:projectId/glyphs`
- `POST /api/projects/:projectId/jobs`
- `GET /api/jobs/:jobId`
- `POST /api/uploads/token`
- `POST /api/uploads/local` (개발 전용)

## 워커 내부 API
모든 요청은 `x-handfont-worker-secret` 헤더가 필요합니다.

- `POST /api/internal/worker/lease` (local queue 전용)
- `GET /api/internal/jobs/:jobId/manifest`
- `POST /api/internal/jobs/:jobId/progress`
- `POST /api/internal/jobs/:jobId/complete`
- `POST /api/internal/jobs/:jobId/fail`
