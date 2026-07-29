import type { GlyphResult, JobKind, StyleSettings } from '@handfont/contracts';
import { sql } from './db';
import { makeId } from './ids';

export const defaultStyle: StyleSettings = {
  weight: 0,
  width: 100,
  slant: 0,
  roundness: 0,
  spacing: 0,
  lineHeight: 150,
};

export async function listProjects(ownerId: string) {
  return sql`
    select * from projects
    where owner_id=${ownerId}
    order by updated_at desc`;
}

export async function getOwnedProject(projectId: string, ownerId: string) {
  const [row] = await sql`
    select * from projects
    where id=${projectId} and owner_id=${ownerId}`;
  return row ?? null;
}

/** Worker-only lookup. Public routes must use getOwnedProject. */
export async function getProject(projectId: string) {
  const [row] = await sql`select * from projects where id=${projectId}`;
  return row ?? null;
}

export async function createProject(
  ownerId: string,
  input: {
    name: string;
    familyName: string;
    description?: string;
  },
) {
  const id = makeId('prj');
  const [row] = await sql`
    insert into projects (id,owner_id,name,family_name,description,style)
    values (${id},${ownerId},${input.name},${input.familyName},${input.description ?? ''},${sql.json(defaultStyle)})
    returning *`;
  return row;
}

export async function listUploads(projectId: string) {
  return sql`select * from uploads where project_id=${projectId} order by created_at`;
}

export async function createUpload(input: {
  ownerId: string;
  projectId: string;
  originalName: string;
  pathname: string;
  blobUrl: string;
  contentType: string;
  size: number;
}) {
  const id = makeId('upl');
  const [row] = await sql`
    insert into uploads (id,project_id,original_name,pathname,blob_url,content_type,size)
    select ${id},p.id,${input.originalName},${input.pathname},${input.blobUrl},${input.contentType},${input.size}
    from projects p
    where p.id=${input.projectId} and p.owner_id=${input.ownerId}
    on conflict (pathname) do update set blob_url=excluded.blob_url, size=excluded.size
    returning *`;
  if (!row) throw new Error('PROJECT_NOT_FOUND');
  await sql`
    update projects set current_step='upload', updated_at=now()
    where id=${input.projectId} and owner_id=${input.ownerId}`;
  return row;
}

export async function listGlyphs(
  projectId: string,
  filters: { status?: string; page?: number; q?: string } = {},
) {
  const status = filters.status && filters.status !== 'all' ? filters.status : null;
  const page = filters.page || null;
  const q = filters.q ? `%${filters.q}%` : null;
  return sql`
    select * from glyphs
    where project_id=${projectId}
      and (${status}::text is null or status=${status})
      and (${page}::int is null or page=${page})
      and (${q}::text is null or character ilike ${q} or unicode ilike ${q} or cell_id ilike ${q})
    order by page, cell_id`;
}

export async function replaceGlyphs(projectId: string, glyphs: GlyphResult[]) {
  await sql.begin(async (tx: any) => {
    await tx`delete from glyphs where project_id=${projectId}`;
    for (const glyph of glyphs) {
      await tx`
        insert into glyphs
        (project_id,page,cell_id,character,unicode,status,raw_iou,tolerant_f1,ink_ratio,svg_url,metadata_url)
        values (${projectId},${glyph.page},${glyph.cellId},${glyph.character},${glyph.unicode},${glyph.status},
          ${glyph.rawIou},${glyph.tolerantF1},${glyph.inkRatio},${glyph.svgUrl},${glyph.metadataUrl})`;
    }
    const reviewCount = glyphs.filter((glyph) => glyph.status !== 'ok').length;
    await tx`
      update projects
      set glyph_count=${glyphs.length}, review_count=${reviewCount}, current_step='review',
          status='ready', progress=55, updated_at=now()
      where id=${projectId}`;
  });
}

export async function createJob(
  ownerId: string,
  projectId: string,
  kind: JobKind,
  payload: Record<string, unknown>,
) {
  const id = makeId('job');
  const idempotencyKey = `${projectId}:${kind}:${Date.now()}`;
  const [row] = await sql`
    insert into jobs (id,project_id,kind,payload,idempotency_key)
    select ${id},p.id,${kind},${sql.json(payload)},${idempotencyKey}
    from projects p
    where p.id=${projectId} and p.owner_id=${ownerId}
    returning *`;
  if (!row) throw new Error('PROJECT_NOT_FOUND');
  return row;
}

/** Worker-only lookup. Public routes must use getOwnedJob. */
export async function getJob(jobId: string) {
  const [row] = await sql`select * from jobs where id=${jobId}`;
  return row ?? null;
}

export async function getOwnedJob(jobId: string, ownerId: string) {
  const [row] = await sql`
    select j.* from jobs j
    join projects p on p.id=j.project_id
    where j.id=${jobId} and p.owner_id=${ownerId}`;
  return row ?? null;
}

export async function getLatestCompletedExport(projectId: string) {
  const [row] = await sql`
    select * from jobs
    where project_id=${projectId}
      and kind='export'
      and status='complete'
      and artifact_url is not null
    order by updated_at desc
    limit 1`;
  return row ?? null;
}

export async function getActiveProjectJob(projectId: string) {
  const [row] = await sql`
    select id, kind, status from jobs
    where project_id=${projectId}
      and status in ('queued','leased','running')
    order by created_at
    limit 1`;
  return row ?? null;
}

export async function listProjectAssetUrls(projectId: string): Promise<string[]> {
  const rows = await sql`
    select url from (
      select blob_url as url from uploads where project_id=${projectId}
      union
      select svg_url as url from glyphs where project_id=${projectId}
      union
      select metadata_url as url from glyphs where project_id=${projectId}
      union
      select artifact_url as url from jobs
        where project_id=${projectId} and artifact_url is not null
    ) assets
    where url is not null`;
  return rows
    .map((row: { url?: unknown }) => String(row.url ?? ''))
    .filter(Boolean);
}

export async function deleteProjectRecord(projectId: string, ownerId: string) {
  const [row] = await sql`
    delete from projects
    where id=${projectId} and owner_id=${ownerId}
    returning id`;
  return row ?? null;
}

export async function updateJob(
  jobId: string,
  patch: {
    status?: string;
    progress?: number;
    message?: string;
    result?: unknown;
    artifactUrl?: string | null;
    error?: string | null;
  },
) {
  const [row] = await sql`
    update jobs set
      status=coalesce(${patch.status ?? null},status),
      progress=coalesce(${patch.progress ?? null},progress),
      message=coalesce(${patch.message ?? null},message),
      result=coalesce(${patch.result ? sql.json(patch.result) : null}::jsonb,result),
      artifact_url=coalesce(${patch.artifactUrl ?? null},artifact_url),
      error=${patch.error ?? null}, updated_at=now()
    where id=${jobId} returning *`;
  return row ?? null;
}

export async function leaseNextJob() {
  return sql.begin(async (tx: any) => {
    const [row] = await tx`
      select * from jobs where status='queued' order by created_at
      for update skip locked limit 1`;
    if (!row) return null;
    const leaseToken = makeId('lease');
    const [leased] = await tx`
      update jobs set status='leased', lease_token=${leaseToken}, attempts=attempts+1, updated_at=now()
      where id=${row.id as string} returning *`;
    return leased;
  });
}

export async function setProjectStyle(
  ownerId: string,
  projectId: string,
  style: StyleSettings,
) {
  const [row] = await sql`
    update projects set style=${sql.json(style)},updated_at=now()
    where id=${projectId} and owner_id=${ownerId} returning *`;
  return row ?? null;
}

export async function blobBelongsToProject(
  ownerId: string,
  projectId: string,
  url: string,
): Promise<boolean> {
  const [row] = await sql`
    select 1 as ok from projects p
    where p.id=${projectId}
      and p.owner_id=${ownerId}
      and exists (
        select 1 from (
          select blob_url as url from uploads where project_id=p.id
          union all select svg_url from glyphs where project_id=p.id
          union all select metadata_url from glyphs where project_id=p.id
          union all select artifact_url from jobs where project_id=p.id and artifact_url is not null
        ) owned where owned.url=${url}
      )
    limit 1`;
  return Boolean(row);
}
