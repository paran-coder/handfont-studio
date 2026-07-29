import { deleteProjectWithAssets, ProjectDeleteError } from '@/lib/project-delete';
import { getProject, listUploads } from '@/lib/repository';
import { jsonError } from '@/lib/security';

export async function GET(
  _: Request,
  { params }: { params: Promise<{ projectId: string }> },
) {
  const { projectId } = await params;
  const project = await getProject(projectId);
  if (!project) return jsonError('프로젝트를 찾을 수 없습니다.', 404);
  return Response.json({ ...project, uploads: await listUploads(projectId) });
}

export async function DELETE(
  _: Request,
  { params }: { params: Promise<{ projectId: string }> },
) {
  try {
    const { projectId } = await params;
    return Response.json(await deleteProjectWithAssets(projectId));
  } catch (error) {
    if (error instanceof ProjectDeleteError) {
      return jsonError(error.message, error.status);
    }
    return jsonError('프로젝트 파일을 정리하지 못했습니다.', 500);
  }
}
