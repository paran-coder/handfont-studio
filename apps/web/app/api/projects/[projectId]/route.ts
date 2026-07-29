import { deleteProjectWithAssets, ProjectDeleteError } from '@/lib/project-delete';
import { requireOwnerId } from '@/lib/owner';
import { getOwnedProject, listUploads } from '@/lib/repository';
import { jsonError, ownerErrorResponse } from '@/lib/security';

export async function GET(
  _: Request,
  { params }: { params: Promise<{ projectId: string }> },
) {
  try {
    const ownerId = await requireOwnerId();
    const { projectId } = await params;
    const project = await getOwnedProject(projectId, ownerId);
    if (!project) return jsonError('프로젝트를 찾을 수 없습니다.', 404);
    const { owner_id: _ownerId, ...publicProject } = project;
    return Response.json({ ...publicProject, uploads: await listUploads(projectId) });
  } catch (error) {
    return ownerErrorResponse(error) ?? jsonError('프로젝트 조회 실패', 500);
  }
}

export async function DELETE(
  _: Request,
  { params }: { params: Promise<{ projectId: string }> },
) {
  try {
    const ownerId = await requireOwnerId();
    const { projectId } = await params;
    return Response.json(await deleteProjectWithAssets(ownerId, projectId));
  } catch (error) {
    const ownerResponse = ownerErrorResponse(error);
    if (ownerResponse) return ownerResponse;
    if (error instanceof ProjectDeleteError) {
      return jsonError(error.message, error.status);
    }
    return jsonError('프로젝트 파일을 정리하지 못했습니다.', 500);
  }
}
