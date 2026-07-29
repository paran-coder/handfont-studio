import { timingSafeEqual } from 'node:crypto';
import { env } from './env';
import { OwnerCookieError } from './owner';

export function requireWorker(request: Request): void {
  const provided = request.headers.get('x-handfont-worker-secret') ?? '';
  const expected = env.workerSecret;
  const a = Buffer.from(provided);
  const b = Buffer.from(expected);
  if (a.length !== b.length || !timingSafeEqual(a, b)) {
    throw new Error('WORKER_UNAUTHORIZED');
  }
}

export function jsonError(message: string, status = 400): Response {
  return Response.json({ detail: message }, { status });
}

export function ownerErrorResponse(error: unknown): Response | null {
  if (error instanceof OwnerCookieError) {
    return jsonError(error.message, 401);
  }
  return null;
}
