import { get } from '@vercel/blob';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { env } from '@/lib/env';
import { requireOwnerId } from '@/lib/owner';
import { blobBelongsToProject } from '@/lib/repository';
import { jsonError, ownerErrorResponse } from '@/lib/security';

export async function GET(request: Request) {
  try {
    const ownerId = await requireOwnerId();
    const urlObject = new URL(request.url);
    const projectId = urlObject.searchParams.get('projectId') ?? '';
    const url = urlObject.searchParams.get('url') ?? '';
    if (!projectId || !url) return jsonError('projectId와 url이 필요합니다.');
    if (!(await blobBelongsToProject(ownerId, projectId, url))) {
      return jsonError('프로젝트 파일을 찾을 수 없습니다.', 404);
    }

    const download = urlObject.searchParams.get('download') === '1';
    if (url.startsWith('local://')) {
      const raw = url.slice('local://'.length).replace(/^\/+/, '');
      const base = path.resolve(env.localBlobDir);
      const target = path.resolve(base, raw);
      if (!target.startsWith(`${base}${path.sep}`)) {
        return jsonError('잘못된 파일 경로입니다.', 400);
      }
      const body = await readFile(target);
      return new Response(body, {
        headers: {
          'content-type': guess(target),
          'content-disposition': download
            ? `attachment; filename="${path.basename(target)}"`
            : 'inline',
          'cache-control': 'private, no-store',
          'x-content-type-options': 'nosniff',
        },
      });
    }

    const result = await get(url, { access: 'private', useCache: false });
    if (!result || result.statusCode !== 200) {
      return jsonError('Blob을 찾을 수 없습니다.', 404);
    }
    return new Response(result.stream, {
      headers: {
        'content-type': result.blob.contentType || 'application/octet-stream',
        'content-disposition': download
          ? `attachment; filename="${result.blob.pathname.split('/').at(-1) || 'download'}"`
          : 'inline',
        'cache-control': 'private, no-store',
        'x-content-type-options': 'nosniff',
      },
    });
  } catch (error) {
    return ownerErrorResponse(error) ?? jsonError('파일 조회 실패', 500);
  }
}

function guess(name: string) {
  const lower = name.toLowerCase();
  if (lower.endsWith('.svg')) return 'image/svg+xml';
  if (lower.endsWith('.png')) return 'image/png';
  if (lower.endsWith('.jpg') || lower.endsWith('.jpeg')) return 'image/jpeg';
  if (lower.endsWith('.json')) return 'application/json';
  if (lower.endsWith('.zip')) return 'application/zip';
  return 'application/octet-stream';
}
