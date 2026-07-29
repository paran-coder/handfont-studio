import type { JobKind, QueueMessage } from '@handfont/contracts';
import { env } from '@/lib/env';
import { readJson } from '@/lib/http';
import { requireOwnerId } from '@/lib/owner';
import { publishJob } from '@/lib/queue';
import {
  createJob,
  getOwnedProject,
  listGlyphs,
  listUploads,
} from '@/lib/repository';
import { jsonError, ownerErrorResponse } from '@/lib/security';

export async function POST(
  request: Request,
  { params }: { params: Promise<{ projectId: string }> },
) {
  try {
    const ownerId = await requireOwnerId();
    const { projectId } = await params;
    const project: any = await getOwnedProject(projectId, ownerId);
    if (!project) return jsonError('프로젝트를 찾을 수 없습니다.', 404);

    const body = await readJson<{
      kind: JobKind;
      payload?: Record<string, unknown>;
    }>(request);
    if (!['process', 'export'].includes(body.kind)) {
      return jsonError('지원하지 않는 작업입니다.');
    }
    if (body.kind === 'process' && (await listUploads(projectId)).length === 0) {
      return jsonError('먼저 작성본을 업로드하십시오.', 409);
    }
    if (body.kind === 'export' && (await listGlyphs(projectId)).length === 0) {
      return jsonError('먼저 작성본 분석을 완료하십시오.', 409);
    }

    const job: any = await createJob(
      ownerId,
      projectId,
      body.kind,
      body.payload ?? {},
    );
    const message: QueueMessage = {
      schemaVersion: '3.3.0',
      jobId: job.id,
      projectId,
      kind: body.kind,
      idempotencyKey: job.idempotency_key,
      callbackBaseUrl: env.appBaseUrl,
    };
    const queued = await publishJob(message);
    return Response.json(
      { ...job, queue_message_id: queued.messageId },
      { status: 202 },
    );
  } catch (error) {
    return ownerErrorResponse(error) ?? jsonError('작업 시작 실패', 500);
  }
}
