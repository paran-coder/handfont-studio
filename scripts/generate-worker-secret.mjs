#!/usr/bin/env node
import { randomBytes } from 'node:crypto';

const bytes = Number(process.argv[2] ?? 48);
if (!Number.isInteger(bytes) || bytes < 32 || bytes > 128) {
  console.error('사용법: node scripts/generate-worker-secret.mjs [32~128 bytes]');
  process.exit(1);
}

console.log(randomBytes(bytes).toString('base64url'));
