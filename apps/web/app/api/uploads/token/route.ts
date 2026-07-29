import { handleUpload, type HandleUploadBody } from '@vercel/blob/client';
import { createUpload, getProject } from '@/lib/repository';
import { env } from '@/lib/env';
import { jsonError } from '@/lib/security';

export async function POST(request: Request) {
  if (env.storageDriver === 'local') {
    return jsonError(
      '로컬 저장소에서는 /api/uploads/local을 사용하십시오.',
      409,
    );
  }

  const body = (await request.json()) as HandleUploadBody;

  try {
    const response = await handleUpload({
      body,
      request,
      onBeforeGenerateToken: async (
        _pathname: string,
        clientPayload: string | null,
      ) => {
        const payload = JSON.parse(clientPayload ?? '{}');

        if (!payload.projectId || !(await getProject(payload.projectId))) {
          throw new Error('PROJECT_NOT_FOUND');
        }

        if (Number(payload.size) > env.maxUploadBytes) {
          throw new Error('FILE_TOO_LARGE');
        }

        return {
          allowedContentTypes: [
            'image/jpeg',
            'image/png',
            'image/webp',
            'application/pdf',
          ],
          maximumSizeInBytes: env.maxUploadBytes,
          addRandomSuffix: true,
          tokenPayload: clientPayload,
        };
      },
      onUploadCompleted: async ({ blob, tokenPayload }) => {
        const payload = JSON.parse(tokenPayload ?? '{}');

        await createUpload({
          projectId: payload.projectId,
          originalName:
            payload.originalName ??
            blob.pathname.split('/').at(-1) ??
            'upload',
          pathname: blob.pathname,
          blobUrl: blob.url,
          contentType: payload.contentType ?? 'application/octet-stream',
          size: Number(payload.size ?? 0),
        });
      },
    });

    return Response.json(response);
  } catch (error) {
    return jsonError(
      error instanceof Error ? error.message : '업로드 토큰 생성 실패',
      400,
    );
  }
}
