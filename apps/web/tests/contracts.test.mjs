import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

test('package version and deployment dependencies', async () => {
  const p = JSON.parse(await readFile(new URL('../package.json', import.meta.url)));
  assert.equal(p.version, '3.3.1');
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
