import type { GlyphResult, JobKind, StyleSettings } from '@handfont/contracts';
import { sql } from './db';
import { makeId } from './ids';

export const defaultStyle: StyleSettings = {
  weight: 0, width: 100, slant: 0, roundness: 0, spacing: 0, lineHeight: 150,
};

export async function listProjects() {
  return sql`select * from projects order by updated_at desc`;
}
export async function getProject(projectId: string) {
  const [row] = await sql`select * from projects where id=${projectId}`;
  return row ?? null;
}
export async function createProject(input: {name:string; familyName:string; description?:string}) {
  const id = makeId('prj');
  const [row] = await sql`
    insert into projects (id,name,family_name,description,style)
    values (${id},${input.name},${input.familyName},${input.description ?? ''},${sql.json(defaultStyle)})
    returning *`;
  return row;
}
export async function listUploads(projectId: string) {
  return sql`select * from uploads where project_id=${projectId} order by created_at`;
}
export async function createUpload(input: {projectId:string; originalName:string; pathname:string; blobUrl:string; contentType:string; size:number}) {
  const id = makeId('upl');
  const [row] = await sql`
    insert into uploads (id,project_id,original_name,pathname,blob_url,content_type,size)
    values (${id},${input.projectId},${input.originalName},${input.pathname},${input.blobUrl},${input.contentType},${input.size})
    on conflict (pathname) do update set blob_url=excluded.blob_url, size=excluded.size
    returning *`;
  await sql`update projects set current_step='upload', updated_at=now() where id=${input.projectId}`;
  return row;
}
export async function listGlyphs(projectId: string, filters: {status?:string; page?:number; q?:string}={}) {
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
    const reviewCount = glyphs.filter(g => g.status !== 'ok').length;
    await tx`update projects set glyph_count=${glyphs.length}, review_count=${reviewCount}, current_step='review', status='ready', progress=55, updated_at=now() where id=${projectId}`;
  });
}
export async function createJob(projectId: string, kind: JobKind, payload: Record<string, unknown>) {
  const id = makeId('job');
  const idempotencyKey = `${projectId}:${kind}:${Date.now()}`;
  const [row] = await sql`
    insert into jobs (id,project_id,kind,payload,idempotency_key)
    values (${id},${projectId},${kind},${sql.json(payload)},${idempotencyKey}) returning *`;
  return row;
}
export async function getJob(jobId: string) {
  const [row] = await sql`select * from jobs where id=${jobId}`;
  return row ?? null;
}
export async function updateJob(jobId: string, patch: {status?:string; progress?:number; message?:string; result?:unknown; artifactUrl?:string|null; error?:string|null}) {
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
export async function setProjectStyle(projectId: string, style: StyleSettings) {
  const [row] = await sql`update projects set style=${sql.json(style)},updated_at=now() where id=${projectId} returning *`;
  return row ?? null;
}

export async function blobBelongsToProject(projectId: string, url: string): Promise<boolean> {
  const [row] = await sql`
    select 1 as ok from (
      select blob_url as url from uploads where project_id=${projectId}
      union all select svg_url from glyphs where project_id=${projectId}
      union all select metadata_url from glyphs where project_id=${projectId}
      union all select artifact_url from jobs where project_id=${projectId} and artifact_url is not null
    ) owned where owned.url=${url} limit 1`;
  return Boolean(row);
}
