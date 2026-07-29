import Link from 'next/link';
import { notFound } from 'next/navigation';
import { JobButton } from '@/components/JobButton';
import { ProjectDeleteButton } from '@/components/ProjectDeleteButton';
import { TemplateDownloads } from '@/components/TemplateDownloads';
import { UploadClient } from '@/components/UploadClient';
import {
  getLatestCompletedExport,
  getProject,
  listGlyphs,
  listUploads,
} from '@/lib/repository';

export const dynamic = 'force-dynamic';

export default async function Project({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const project: any = await getProject(projectId);
  if (!project) notFound();

  const uploads = (await listUploads(projectId)) as any[];
  const glyphs = (await listGlyphs(projectId)) as any[];
  const latestExport: any = await getLatestCompletedExport(projectId);

  return (
    <main className="page">
      <div className="sectionHead projectTitleRow">
        <div>
          <h1>{project.name}</h1>
          <p className="muted">{project.family_name}</p>
        </div>
        <div className="projectTitleActions">
          <span
            className={`badge ${project.status === 'ready' || project.status === 'complete' ? 'badgeReady' : ''}`}
          >
            {project.status}
          </span>
          <ProjectDeleteButton
            projectId={projectId}
            projectName={project.name}
            redirectHome
          />
        </div>
      </div>

      <section className="grid grid4">
        <div className="card">
          <strong>{uploads.length}</strong>
          <p className="muted">업로드 파일</p>
        </div>
        <div className="card">
          <strong>{project.glyph_count}</strong>
          <p className="muted">글리프</p>
        </div>
        <div className="card">
          <strong>{project.review_count}</strong>
          <p className="muted">검수 필요</p>
        </div>
        <div className="card">
          <strong>{project.progress}%</strong>
          <p className="muted">진행률</p>
        </div>
      </section>

      <div className="sectionHead">
        <div>
          <h2>1. 작성본 업로드</h2>
          <p className="muted sectionDescription">
            양식이 없다면 PDF 또는 PNG 묶음을 먼저 내려받으십시오.
          </p>
        </div>
        <TemplateDownloads />
      </div>
      <UploadClient projectId={projectId} />
      <div className="uploadList">
        {uploads.map((upload: any) => (
          <div className="uploadItem" key={upload.id}>
            <span>{upload.original_name}</span>
            <span className="badge">{upload.status}</span>
          </div>
        ))}
      </div>

      <div className="sectionHead">
        <h2>2. 분석 작업</h2>
      </div>
      <div className="card">
        <JobButton projectId={projectId} kind="process" label="작성본 분석 시작" />
      </div>

      <div className="sectionHead">
        <h2>3. 글리프 검수</h2>
        <Link href={`/projects/${projectId}/review`}>전체 보기 →</Link>
      </div>
      <div className="glyphGrid">
        {glyphs.slice(0, 20).map((glyph: any) => (
          <div className="glyph" key={glyph.id}>
            <div className="glyphPreview">
              <img
                src={`/api/blob?projectId=${projectId}&url=${encodeURIComponent(glyph.svg_url)}`}
                alt={glyph.character}
              />
            </div>
            <div className="glyphMeta">
              <strong>{glyph.character}</strong>
              <span>{glyph.status}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="sectionHead">
        <h2>4. 폰트 내보내기</h2>
      </div>
      <div className="card exportCard">
        <JobButton projectId={projectId} kind="export" label="TTF 패키지 생성" />
        {latestExport?.artifact_url ? (
          <div className="savedArtifact">
            <div>
              <strong>완성된 결과가 저장되어 있습니다.</strong>
              <p className="muted">가장 최근에 완료된 TTF 패키지입니다.</p>
            </div>
            <a
              className="button buttonSoft"
              href={`/api/blob?projectId=${projectId}&url=${encodeURIComponent(latestExport.artifact_url)}&download=1`}
            >
              완성 결과 다시 다운로드
            </a>
          </div>
        ) : null}
      </div>
    </main>
  );
}
