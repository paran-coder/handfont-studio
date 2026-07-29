import { asNumber } from '@/lib/http';
import { requireOwnerId } from '@/lib/owner';
import { getOwnedProject, listGlyphs } from '@/lib/repository';
import { jsonError, ownerErrorResponse } from '@/lib/security';

export async function GET(
  request: Request,
  { params }: { params: Promise<{ projectId: string }> },
) {
  try {
    const ownerId = await requireOwnerId();
    const { projectId } = await params;
    if (!(await getOwnedProject(projectId, ownerId))) {
      return jsonError('프로젝트를 찾을 수 없습니다.', 404);
    }
    const url = new URL(request.url);
    return Response.json(
      await listGlyphs(projectId, {
        status: url.searchParams.get('status') ?? undefined,
        page: asNumber(url.searchParams.get('page')),
        q: url.searchParams.get('q') ?? undefined,
      }),
    );
  } catch (error) {
    return ownerErrorResponse(error) ?? jsonError('글리프 조회 실패', 500);
  }
}
