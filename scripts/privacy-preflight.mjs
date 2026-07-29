#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { readFile, readdir, stat } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const root = path.resolve(new URL('..', import.meta.url).pathname);
const ignoredDirs = new Set(['.git', 'node_modules', '.next', '.vercel', '.venv', '__pycache__', '.pytest_cache']);
const forbiddenNames = [
  /Screenshot_\d+_Flexcil\.(?:jpg|jpeg|png|webp)$/i,
  /Flexcil/i,
];
const forbiddenPublicDemoNames = new Set(['rectified-pages.jpg', 'glyph-grid.png', 'font-specimen.png']);
const forbiddenText = [
  ['사용자 데모 프로젝트명', ['나의 디지털',' 손글씨'].join('')],
  ['사용자 샘플 설명', ['Flexcil',' 실제 디지털',' 작성본 105자 데모'].join('')],
  ['Base64 SVG 글리프 임베딩', ['data:image/svg+xml',';base64,'].join('')],
  ['원본 샘플 파일명', ['Screenshot','_20260729_131752','_Flexcil.jpg'].join('')],
  ['원본 샘플 파일명', ['Screenshot','_20260729_131756','_Flexcil.jpg'].join('')],
  ['원본 샘플 파일명', ['Screenshot','_20260729_131759','_Flexcil.jpg'].join('')],
];
const forbiddenHashes = new Map([
  ['c282808a9974d5af970a15135169c3b06e5d4da3f7ba74e9498599c05a3de5e1', '원본 Flexcil 스크린샷 1'],
  ['fc002cf75576e68febe56b34f20bd67907648d865bc9c862e888255828826d37', '원본 Flexcil 스크린샷 2'],
  ['d123ff1605adbbf486259d1d8de6f12729d789ce34f9dbefea468e8bf86ae740', '원본 Flexcil 스크린샷 3'],
  ['35f035610103484622adf3a31dd3ef2e2b28674213a3880bff6362d9539cfba8', '사용자 파생 보정 페이지'],
  ['f1a312fa0a4c3393b5d8a0a326141490bba976a8ab980304bcceabbe93de305e', '사용자 파생 글리프 검수표'],
  ['3a317d9215023af3e5a5254b1b769e631f59e0de2f1418ce0ca904b5591d6475', '사용자 파생 폰트 미리보기'],
]);

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
for (const file of files) {
  const rel = path.relative(root, file).split(path.sep).join('/');
  const base = path.basename(file);
  if (forbiddenNames.some(pattern => pattern.test(base))) errors.push(`금지된 사용자 샘플 파일명: /${rel}`);
  if (rel.startsWith('apps/web/public/demo/') && forbiddenPublicDemoNames.has(base)) {
    errors.push(`공개 데모 폴더에 사용자 파생 산출물 이름 포함: /${rel}`);
  }

  const bytes = await readFile(file);
  const hash = createHash('sha256').update(bytes).digest('hex');
  if (forbiddenHashes.has(hash)) errors.push(`${forbiddenHashes.get(hash)} 해시 발견: /${rel}`);

  if (rel !== 'scripts/privacy-preflight.mjs' && bytes.length <= 12_000_000) {
    const source = bytes.toString('utf8');
    for (const [label, needle] of forbiddenText) {
      if (source.includes(needle)) errors.push(`${label} 발견: /${rel}`);
    }
  }
}

if (errors.length) {
  console.error(`개인정보 사전 검사 실패: ${errors.length}건`);
  for (const item of errors) console.error(`- ${item}`);
  process.exit(1);
}
console.log(`개인정보 사전 검사 통과: ${files.length}개 파일`);
