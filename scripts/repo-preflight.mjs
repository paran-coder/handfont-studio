#!/usr/bin/env node
import { readFile, readdir, stat } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const root = path.resolve(new URL('..', import.meta.url).pathname);
const ignoredDirs = new Set(['.git', 'node_modules', '.next', '.vercel', '.venv', '__pycache__', '.pytest_cache']);
const forbiddenExtensions = new Set(['.ttf', '.otf', '.woff', '.woff2', '.db', '.sqlite']);
const forbiddenParts = ['/runtime/', '/worker-runtime/'];
const textExtensions = new Set(['.js', '.mjs', '.cjs', '.ts', '.tsx', '.json', '.md', '.yml', '.yaml', '.toml', '.env', '.example', '.sh', '.sql', '.txt', '.css']);
const suspiciousPatterns = [
  ['GitHub token', /gh[pousr]_[A-Za-z0-9_]{30,}/g],
  ['Vercel token', /(?:VERCEL_TOKEN[ \t]*=[ \t]*)(?!$|<|replace|example)[^\s#]{16,}/gim],
  ['Blob token', /(?:BLOB_READ_WRITE_TOKEN[ \t]*=[ \t]*)(?!$|<|replace|example)[^\s#]{20,}/gim],
  ['Private key', /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/g],
  ['PostgreSQL credential', /postgres(?:ql)?:\/\/[^:\s]+:[^@\s]+@/g],
];

const files = [];
async function walk(dir) {
  for (const name of await readdir(dir)) {
    if (ignoredDirs.has(name)) continue;
    const file = path.join(dir, name);
    const info = await stat(file);
    if (info.isDirectory()) await walk(file);
    else files.push(file);
  }
}
await walk(root);

const errors = [];
const warnings = [];
for (const file of files) {
  const rel = `/${path.relative(root, file).split(path.sep).join('/')}`;
  const ext = path.extname(file).toLowerCase();
  if (forbiddenExtensions.has(ext)) errors.push(`금지된 바이너리/DB 파일: ${rel}`);
  if (forbiddenParts.some(part => rel.includes(part))) errors.push(`런타임 파일 경로 포함: ${rel}`);
  if (!textExtensions.has(ext) && !file.endsWith('.env.example') && !file.endsWith('.gitignore') && !file.endsWith('.dockerignore')) continue;
  const source = await readFile(file, 'utf8').catch(() => '');
  for (const [label, pattern] of suspiciousPatterns) {
    if (label === 'PostgreSQL credential' && (rel.endsWith('.example') || rel.includes('/docs/') || rel.includes('/.github/workflows/'))) continue;
    pattern.lastIndex = 0;
    if (pattern.test(source)) errors.push(`${label} 후보 발견: ${rel}`);
  }
}

const required = [
  'README.md', 'User manual.md', 'context-notes.md', 'checklist.md', 'SECURITY.md', 'CONTRIBUTING.md',
  '.github/workflows/ci.yml', '.github/pull_request_template.md', '.github/dependabot.yml',
  'docs/github-first-push-v3.3.1.md', 'docs/deployment-checklist-v3.3.1.md',
  'docs/environment-variables-v3.3.1.md', 'docs/post-deploy-smoke-test-v3.3.1.md',
  'infrastructure/vercel/project-settings-v3.3.1.json'
];
const relFiles = new Set(files.map(file => path.relative(root, file).split(path.sep).join('/')));
for (const name of required) if (!relFiles.has(name)) errors.push(`필수 파일 누락: /${name}`);

const packageFiles = ['package.json', 'apps/web/package.json', 'packages/contracts/package.json', 'workers/font-engine/package.json'];
for (const name of packageFiles) {
  const parsed = JSON.parse(await readFile(path.join(root, name), 'utf8'));
  if (parsed.version !== '3.3.1') errors.push(`버전 불일치: /${name} = ${parsed.version}`);
}

const gitignore = await readFile(path.join(root, '.gitignore'), 'utf8');
for (const item of ['.env', '.vercel/', 'runtime/', 'worker-runtime/', '*.ttf', '*.otf', '*.woff', '*.woff2']) {
  if (!gitignore.includes(item)) errors.push(`.gitignore 필수 패턴 누락: ${item}`);
}

if (!relFiles.has('pnpm-lock.yaml')) warnings.push('pnpm-lock.yaml이 없습니다. 네트워크가 가능한 환경에서 pnpm install 후 커밋하십시오.');

if (errors.length) {
  console.error(`저장소 사전 검사 실패: ${errors.length}건`);
  for (const item of errors) console.error(`- ${item}`);
  for (const item of warnings) console.warn(`- 경고: ${item}`);
  process.exit(1);
}

console.log(`저장소 사전 검사 통과: ${files.length}개 파일`);
for (const item of warnings) console.warn(`- 경고: ${item}`);
