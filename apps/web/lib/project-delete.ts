import { del } from '@vercel/blob';
import { rm } from 'node:fs/promises';
import path from 'node:path';
import { env } from './env';
import {
  deleteProjectRecord,
  getActiveProjectJob,
  getOwnedProject,
  listProjectAssetUrls,
} from './repository';

export class ProjectDeleteError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = 'ProjectDeleteError';
  }
}

export async function deleteProjectWithAssets(
  ownerId: string,
  projectId: string,
) {
  const project = await getOwnedProject(projectId, ownerId);
  if (!project) {
    throw new ProjectDeleteError('프로젝트를 찾을 수 없습니다.', 404);
  }

  const activeJob = await getActiveProjectJob(projectId);
  if (activeJob) {
    throw new ProjectDeleteError(
      '분석 또는 폰트 생성 작업이 진행 중입니다. 작업이 끝난 뒤 삭제하십시오.',
      409,
    );
  }

  const urls = [...new Set(await listProjectAssetUrls(projectId))];
  const localUrls = urls.filter((url) => url.startsWith('local://'));
  const remoteUrls = urls.filter((url) => !url.startsWith('local://'));

  for (const url of localUrls) {
    await removeLocalAsset(url);
  }
  if (remoteUrls.length > 0) {
    await del(remoteUrls);
  }

  const deleted = await deleteProjectRecord(projectId, ownerId);
  if (!deleted) {
    throw new ProjectDeleteError('프로젝트 삭제에 실패했습니다.', 500);
  }

  return {
    id: projectId,
    deletedAssets: urls.length,
  };
}

async function removeLocalAsset(url: string): Promise<void> {
  const raw = url.slice('local://'.length).replace(/^\/+/, '');
  const base = path.resolve(env.localBlobDir);
  const target = path.resolve(base, raw);
  if (target !== base && !target.startsWith(`${base}${path.sep}`)) {
    throw new ProjectDeleteError('잘못된 로컬 파일 경로가 발견되었습니다.', 400);
  }
  await rm(target, { force: true });
}
