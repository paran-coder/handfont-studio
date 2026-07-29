import { requireOwnerId } from '@/lib/owner';
import { getOwnedJob } from '@/lib/repository';
import { jsonError, ownerErrorResponse } from '@/lib/security';

export async function GET(
  _: Request,
  { params }: { params: Promise<{ jobId: string }> },
) {
  try {
    const ownerId = await requireOwnerId();
    const { jobId } = await params;
    const job = await getOwnedJob(jobId, ownerId);
    return job
      ? Response.json(job)
      : jsonError('작업을 찾을 수 없습니다.', 404);
  } catch (error) {
    return ownerErrorResponse(error) ?? jsonError('작업 조회 실패', 500);
  }
}
