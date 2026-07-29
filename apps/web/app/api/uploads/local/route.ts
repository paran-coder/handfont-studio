import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { env } from '@/lib/env';
import { requireOwnerId } from '@/lib/owner';
import { createUpload, getOwnedProject } from '@/lib/repository';
import { jsonError, ownerErrorResponse } from '@/lib/security';

export async function POST(request: Request) {
  try {
    if (env.storageDriver !== 'local') {
      return jsonError('운영 저장소에서는 직접 Blob 업로드를 사용하십시오.', 409);
    }
    const ownerId = await requireOwnerId();
    const form = await request.formData();
    const projectId = String(form.get('projectId') ?? '');
    const file = form.get('file');
    if (!projectId || !(await getOwnedProject(projectId, ownerId))) {
      return jsonError('프로젝트를 찾을 수 없습니다.', 404);
    }
    if (!(file instanceof File)) return jsonError('파일이 없습니다.');
    if (file.size > env.maxUploadBytes) {
      return jsonError('파일 크기 제한을 초과했습니다.', 413);
    }
    const allowed = ['image/jpeg', 'image/png', 'image/webp', 'application/pdf'];
    if (!allowed.includes(file.type)) {
      return jsonError('지원하지 않는 파일 형식입니다.', 415);
    }

    const pathname = `projects/${projectId}/uploads/${Date.now()}-${file.name.replace(/[^A-Za-z0-9가-힣._-]/g, '-')}`;
    const target = path.resolve(env.localBlobDir, pathname);
    await mkdir(path.dirname(target), { recursive: true });
    await writeFile(target, Buffer.from(await file.arrayBuffer()));
    return Response.json(
      await createUpload({
        ownerId,
        projectId,
        originalName: file.name,
        pathname,
        blobUrl: `local://${pathname}`,
        contentType: file.type,
        size: file.size,
      }),
      { status: 201 },
    );
  } catch (error) {
    return ownerErrorResponse(error) ?? jsonError('업로드 실패', 500);
  }
}
