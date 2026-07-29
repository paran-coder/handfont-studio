import test from 'node:test';
import assert from 'node:assert/strict';
import { access, readFile, stat } from 'node:fs/promises';

const appRoot = new URL('../', import.meta.url);

test('package version and deployment dependencies', async () => {
  const p = JSON.parse(await readFile(new URL('../package.json', import.meta.url)));
  assert.equal(p.version, '3.3.4');
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
  assert.match(service, /getActiveProjectJob/);
  assert.match(service, /await del\(remoteUrls\)/);
  assert.match(service, /deleteProjectRecord/);
});

test('project page exposes saved export download', async () => {
  const page = await readFile(new URL('../app/projects/[projectId]/page.tsx', import.meta.url), 'utf8');
  assert.match(page, /getLatestCompletedExport/);
  assert.match(page, /완성 결과 다시 다운로드/);
});
