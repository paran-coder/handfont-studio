#!/usr/bin/env node
import { readFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';

const target = path.resolve(process.argv[2] ?? '.env');
if (!existsSync(target)) {
  console.error(`환경변수 파일을 찾을 수 없습니다: ${target}`);
  process.exit(1);
}

const source = await readFile(target, 'utf8');
const values = new Map();
for (const raw of source.split(/\r?\n/)) {
  const line = raw.trim();
  if (!line || line.startsWith('#')) continue;
  const index = line.indexOf('=');
  if (index < 1) continue;
  values.set(line.slice(0, index).trim(), line.slice(index + 1).trim());
}

const mode = process.argv.includes('--worker') ? 'worker' : 'web';
const required = mode === 'worker'
  ? ['CONTROL_API_BASE_URL', 'WORKER_SHARED_SECRET', 'WORKER_STORAGE_DRIVER', 'QUEUE_DRIVER']
  : ['DATABASE_URL', 'WORKER_SHARED_SECRET', 'STORAGE_DRIVER', 'NEXT_PUBLIC_STORAGE_DRIVER', 'QUEUE_DRIVER'];

const errors = [];
const warnings = [];
for (const name of required) {
  if (!values.get(name)) errors.push(`필수 값 누락: ${name}`);
}

const secret = values.get('WORKER_SHARED_SECRET') ?? '';
if (secret && secret.length < 32) errors.push('WORKER_SHARED_SECRET은 최소 32자여야 합니다.');
if (/replace-with|changeme|example|your-project|<.+>/i.test(secret)) errors.push('WORKER_SHARED_SECRET이 예제 값입니다.');

const storage = values.get(mode === 'worker' ? 'WORKER_STORAGE_DRIVER' : 'STORAGE_DRIVER');
if (storage && !['local', 'vercel'].includes(storage)) errors.push(`지원하지 않는 저장소 드라이버: ${storage}`);
const queue = values.get('QUEUE_DRIVER');
if (queue && !['local', 'vercel'].includes(queue)) errors.push(`지원하지 않는 큐 드라이버: ${queue}`);

if (storage === 'vercel' && !values.get('BLOB_READ_WRITE_TOKEN')) errors.push('Vercel 저장소 사용 시 BLOB_READ_WRITE_TOKEN이 필요합니다.');
if (queue === 'vercel' && !values.get('VERCEL_QUEUE_TOPIC')) errors.push('Vercel Queue 사용 시 VERCEL_QUEUE_TOPIC이 필요합니다.');
if (queue === 'vercel' && !values.get('VERCEL_QUEUE_REGION')) warnings.push('VERCEL_QUEUE_REGION이 없어 기본값 icn1을 사용합니다.');

const databaseUrl = values.get('DATABASE_URL') ?? '';
if (mode === 'web' && databaseUrl && !databaseUrl.startsWith('postgres')) errors.push('DATABASE_URL은 PostgreSQL URL이어야 합니다.');

if (errors.length) {
  console.error('환경변수 검사 실패');
  for (const item of errors) console.error(`- ${item}`);
  for (const item of warnings) console.warn(`- 경고: ${item}`);
  process.exit(1);
}

console.log(`환경변수 검사 통과: ${target} (${mode})`);
for (const item of warnings) console.warn(`- 경고: ${item}`);
