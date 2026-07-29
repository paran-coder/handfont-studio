import { readJson } from '@/lib/http';
import { requireOwnerId } from '@/lib/owner';
import { createProject, listProjects } from '@/lib/repository';
import { jsonError, ownerErrorResponse } from '@/lib/security';

function withoutOwner<T extends Record<string, unknown>>(row: T) {
  const { owner_id: _ownerId, ...project } = row;
  return project;
}

export async function GET() {
  try {
    const ownerId = await requireOwnerId();
    const projects = await listProjects(ownerId);
    return Response.json(projects.map((project: Record<string, unknown>) => withoutOwner(project)));
  } catch (error) {
    return ownerErrorResponse(error) ?? jsonError('프로젝트 목록 조회 실패', 500);
  }
}

export async function POST(request: Request) {
  try {
    const ownerId = await requireOwnerId();
    const body = await readJson<{
      name: string;
      familyName: string;
      description?: string;
    }>(request);
    if (!body.name?.trim() || !body.familyName?.trim()) {
      return jsonError('프로젝트 이름과 폰트 이름이 필요합니다.');
    }
    const project = await createProject(ownerId, {
      name: body.name.trim(),
      familyName: body.familyName.trim(),
      description: body.description?.trim(),
    });
    return Response.json(withoutOwner(project), { status: 201 });
  } catch (error) {
    return (
      ownerErrorResponse(error) ??
      jsonError(error instanceof Error ? error.message : '프로젝트 생성 실패')
    );
  }
}
