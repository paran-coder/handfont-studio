import { notFound } from 'next/navigation';
import { requireOwnerId } from '@/lib/owner';
import { getOwnedProject, listGlyphs } from '@/lib/repository';

export const dynamic = 'force-dynamic';

export default async function Review({
  params,
  searchParams,
}: {
  params: Promise<{ projectId: string }>;
  searchParams: Promise<{ status?: string; page?: string; q?: string }>;
}) {
  const { projectId } = await params;
  const query = await searchParams;
  const ownerId = await requireOwnerId();
  if (!(await getOwnedProject(projectId, ownerId))) notFound();
  const glyphs: any[] = (await listGlyphs(projectId, {
    status: query.status,
    page: query.page ? Number(query.page) : undefined,
    q: query.q,
  })) as any[];

  return (
    <main className="page">
      <h1>글리프 검수</h1>
      <p className="muted">{glyphs.length}개 글리프</p>
      <div className="glyphGrid">
        {glyphs.map((glyph) => (
          <article className="glyph" key={glyph.id}>
            <div className="glyphPreview">
              <img
                src={`/api/blob?projectId=${projectId}&url=${encodeURIComponent(glyph.svg_url)}`}
                alt={`${glyph.character} 글리프`}
              />
            </div>
            <div className="glyphMeta">
              <strong>{glyph.character}</strong>
              <span>{glyph.cell_id}</span>
            </div>
          </article>
        ))}
      </div>
    </main>
  );
}
