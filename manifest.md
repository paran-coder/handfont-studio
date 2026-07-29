# HandFont Studio v3.3.6 Manifest

## 애플리케이션

- `apps/web`: Vercel Next.js 웹·API
- `workers/font-engine`: Docker Python 폰트 워커
- `packages/contracts`: schemaVersion 3.3.0 공용 계약

## v3.3.6 익명 소유권

- `apps/web/proxy.ts`
- `apps/web/lib/owner-config.ts`
- `apps/web/lib/owner.ts`
- `apps/web/lib/repository.ts`
- `apps/web/lib/project-delete.ts`
- `apps/web/app/api/projects/**`
- `apps/web/app/api/jobs/**`
- `apps/web/app/api/uploads/**`
- `apps/web/app/api/blob/route.ts`
- `infrastructure/migrations/0002_anonymous_ownership.sql`

## 기존 사용자 기능

- `apps/web/public/templates/handfont-writing-template.pdf`
- `apps/web/public/templates/handfont-writing-template-png.zip`
- `apps/web/components/TemplateDownloads.tsx`
- `apps/web/components/ProjectDeleteButton.tsx`
- `apps/web/app/projects/[projectId]/page.tsx`
- `apps/web/app/page.tsx`

## 핵심 문서

- `README.md`
- `User manual.md`
- `context-notes.md`
- `checklist.md`
- `release-notes-v3.3.6.md`
- `SECURITY.md`
- `CONTRIBUTING.md`

## 배포·검사

- `scripts/privacy-preflight.mjs`
- `scripts/repo-preflight.mjs`
- `scripts/check-env.mjs`
- `infrastructure/migrations/0001_initial.sql`
- `infrastructure/migrations/0002_anonymous_ownership.sql`
- `.github/workflows/ci.yml`
