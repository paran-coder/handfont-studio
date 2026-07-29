export async function readJson<T>(request: Request): Promise<T> {
  const type = request.headers.get('content-type') ?? '';
  if (!type.includes('application/json')) throw new Error('JSON_REQUIRED');
  return request.json() as Promise<T>;
}
export function asNumber(value: string | null): number | undefined {
  if (!value) return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}
