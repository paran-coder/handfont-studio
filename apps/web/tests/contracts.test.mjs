import test from 'node:test';
import assert from 'node:assert/strict';
import { access, readFile, stat } from 'node:fs/promises';

test('package version and deployment dependencies', async () => {
  const p = JSON.parse(await readFile(new URL('../package.json', import.meta.url)));
  assert.equal(p.version, '3.3.6');
  assert.equal(p.dependencies['@vercel/blob'], '2.6.1');
  assert.equal(p.dependencies['@vercel/queue'], '0.4.0');
  assert.ok(p.dependencies.postgres);
});

test('upload route uses private client upload', async () => {
  const s = await readFile(new URL('../components/UploadClient.tsx', import.meta.url), 'utf8');
  assert.match(s, /access:'private'/);
  assert.match(s, /handleUploadUrl:'\/api\/uploads\/token'/);
});

test('queue producer publishes durable message', async () => {
  const s = await readFile(new URL('../lib/queue.ts', import.meta.url), 'utf8');
  assert.match(s, /send\(env\.queueTopic, message\)/);
});

test('app base URL supports Vercel system variables', async () => {
  const s = await readFile(new URL('../lib/env.ts', import.meta.url), 'utf8');
  assert.match(s, /VERCEL_PROJECT_PRODUCTION_URL/);
  assert.match(s, /VERCEL_URL/);
  assert.match(s, /http:\/\/localhost:3000/);
});

test('writing template downloads are packaged', async () => {
  const pdf = new URL('../public/templates/handfont-writing-template.pdf', import.meta.url);
  const pngZip = new URL('../public/templates/handfont-writing-template-png.zip', import.meta.url);
  await access(pdf);
  await access(pngZip);
  assert.ok((await stat(pdf)).size > 100_000);
  assert.ok((await stat(pngZip)).size > 100_000);
});

test('project deletion protects active jobs and removes assets', async () => {
  const route = await readFile(new URL('../app/api/projects/[projectId]/route.ts', import.meta.url), 'utf8');
  const service = await readFile(new URL('../lib/project-delete.ts', import.meta.url), 'utf8');
  assert.match(route, /export async function DELETE/);
  assert.match(route, /requireOwnerId/);
  assert.match(service, /getOwnedProject/);
  assert.match(service, /getActiveProjectJob/);
  assert.match(service, /await del\(remoteUrls\)/);
  assert.match(service, /deleteProjectRecord/);
});

test('project page exposes saved export download', async () => {
  const page = await readFile(new URL('../app/projects/[projectId]/page.tsx', import.meta.url), 'utf8');
  assert.match(page, /getLatestCompletedExport/);
  assert.match(page, /getOwnedProject/);
  assert.match(page, /완성 결과 다시 다운로드/);
});

test('proxy issues an httpOnly browser owner cookie', async () => {
  const proxy = await readFile(new URL('../proxy.ts', import.meta.url), 'utf8');
  assert.match(proxy, /randomBytes\(32\)/);
  assert.match(proxy, /httpOnly: true/);
  assert.match(proxy, /sameSite: 'lax'/);
  assert.match(proxy, /OWNER_COOKIE_NAME/);
});

test('owner token is hashed before database use', async () => {
  const owner = await readFile(new URL('../lib/owner.ts', import.meta.url), 'utf8');
  assert.match(owner, /createHash\('sha256'\)/);
  assert.match(owner, /requireOwnerId/);
});

test('public resources scope database access to owner id', async () => {
  const repository = await readFile(new URL('../lib/repository.ts', import.meta.url), 'utf8');
  const blob = await readFile(new URL('../app/api/blob/route.ts', import.meta.url), 'utf8');
  const job = await readFile(new URL('../app/api/jobs/[jobId]/route.ts', import.meta.url), 'utf8');
  assert.match(repository, /where owner_id=\$\{ownerId\}/);
  assert.match(repository, /getOwnedProject/);
  assert.match(repository, /getOwnedJob/);
  assert.match(blob, /blobBelongsToProject\(ownerId, projectId, url\)/);
  assert.match(job, /getOwnedJob\(jobId, ownerId\)/);
});

test('blob upload preserves verified owner in token payload', async () => {
  const route = await readFile(new URL('../app/api/uploads/token/route.ts', import.meta.url), 'utf8');
  assert.match(route, /getOwnedProject\(payload\.projectId, ownerId\)/);
  assert.match(route, /tokenPayload: JSON\.stringify\(\{ \.\.\.payload, ownerId \}\)/);
  assert.match(route, /getOwnedProject\(payload\.projectId, payload\.ownerId\)/);
});
