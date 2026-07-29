import { createHash } from 'node:crypto';
import { cookies } from 'next/headers';
import { isValidOwnerToken, OWNER_COOKIE_NAME } from './owner-config';

export class OwnerCookieError extends Error {
  constructor(message = '브라우저 식별 정보가 없습니다. 페이지를 새로고침하십시오.') {
    super(message);
    this.name = 'OwnerCookieError';
  }
}

export function hashOwnerToken(token: string): string {
  if (!isValidOwnerToken(token)) throw new OwnerCookieError();
  return createHash('sha256').update(token).digest('hex');
}

export async function requireOwnerId(): Promise<string> {
  const store = await cookies();
  const token = store.get(OWNER_COOKIE_NAME)?.value;
  if (!isValidOwnerToken(token)) throw new OwnerCookieError();
  return hashOwnerToken(token);
}
