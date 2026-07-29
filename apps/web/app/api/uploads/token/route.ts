import { handleUpload, type HandleUploadBody } from '@vercel/blob/client';
import { env } from '@/lib/env';
import { requireOwnerId } from '@/lib/owner';
import { createUpload, getOwnedProject } from '@/lib/repository';
import { jsonError, ownerErrorResponse } from '@/lib/security';

type UploadCompletedArguments = {
  blob: {
    pathname: string;
    url: string;
  };
  tokenPayload?: string | null;
};

type UploadPayload = {
  projectId?: string;
  originalName?: string;
  contentType?: string;
  size?: number;
  ownerId?: string;
};

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
        const ownerId = await requireOwnerId();
        const payload = JSON.parse(clientPayload ?? '{}') as UploadPayload;

        if (
          !payload.projectId ||
          !(await getOwnedProject(payload.projectId, ownerId))
        ) {
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
          tokenPayload: JSON.stringify({ ...payload, ownerId }),
        };
      },
      onUploadCompleted: async ({
        blob,
        tokenPayload,
      }: UploadCompletedArguments) => {
        const payload = JSON.parse(tokenPayload ?? '{}') as UploadPayload;
        if (!payload.projectId || !payload.ownerId) {
          throw new Error('INVALID_UPLOAD_PAYLOAD');
        }
        if (!(await getOwnedProject(payload.projectId, payload.ownerId))) {
          throw new Error('PROJECT_NOT_FOUND');
        }

        await createUpload({
          ownerId: payload.ownerId,
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
    return (
      ownerErrorResponse(error) ??
      jsonError(
        error instanceof Error ? error.message : '업로드 토큰 생성 실패',
        400,
      )
    );
  }
}
