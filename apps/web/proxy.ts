import { randomBytes } from 'node:crypto';
import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';
import {
  isValidOwnerToken,
  OWNER_COOKIE_MAX_AGE,
  OWNER_COOKIE_NAME,
} from './lib/owner-config';

const BYPASS_PREFIXES = [
  '/_next/',
  '/templates/',
  '/api/internal/',
  '/api/health',
  '/api/uploads/token',
];

function shouldBypass(pathname: string): boolean {
  return (
    BYPASS_PREFIXES.some((prefix) => pathname.startsWith(prefix)) ||
    /\.[A-Za-z0-9]{2,8}$/.test(pathname)
  );
}

function attachOwnerCookie(response: NextResponse, request: NextRequest): void {
  response.cookies.set({
    name: OWNER_COOKIE_NAME,
    value: randomBytes(32).toString('base64url'),
    httpOnly: true,
    secure: request.nextUrl.protocol === 'https:',
    sameSite: 'lax',
    path: '/',
    maxAge: OWNER_COOKIE_MAX_AGE,
    priority: 'high',
  });
}

export function proxy(request: NextRequest) {
  if (shouldBypass(request.nextUrl.pathname)) return NextResponse.next();

  const token = request.cookies.get(OWNER_COOKIE_NAME)?.value;
  if (isValidOwnerToken(token)) return NextResponse.next();

  if (request.method === 'GET' || request.method === 'HEAD') {
    const response = NextResponse.redirect(request.nextUrl);
    attachOwnerCookie(response, request);
    return response;
  }

  const response = NextResponse.json(
    { detail: '브라우저 식별 정보를 만들었습니다. 페이지를 새로고침한 뒤 다시 시도하십시오.' },
    { status: 401 },
  );
  attachOwnerCookie(response, request);
  return response;
}

export const config = {
  matcher: '/:path*',
};
