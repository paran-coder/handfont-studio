import Link from 'next/link';
import { ProjectDeleteButton } from '@/components/ProjectDeleteButton';
import { TemplateDownloads } from '@/components/TemplateDownloads';
import { listProjects } from '@/lib/repository';

export const dynamic = 'force-dynamic';

export default async function Home() {
  let projects: any[] = [];
  try {
    projects = (await listProjects()) as any[];
  } catch {
    // The empty state remains usable while the database is being configured.
  }

  return (
    <main className="page">
      <section className="hero">
        <div>
          <p style={{ color: '#f06f4f', fontWeight: 800 }}>HANDFONT CLOUD</p>
          <h1>
            내 손글씨를
            <br />
            설치 가능한 폰트로.
          </h1>
          <p>
            작성 양식을 내려받아 글자를 채운 뒤 업로드하십시오. 독립 워커가
            페이지 보정, SVG 벡터화와 TTF 생성을 처리합니다.
          </p>
          <div className="heroActions">
            <Link className="button buttonAccent" href="/projects/new">
              새 프로젝트
            </Link>
            <TemplateDownloads />
          </div>
        </div>
        <div className="paper">가나다<br />ABC 123</div>
      </section>

      <div className="sectionHead">
        <h2>프로젝트</h2>
        <span className="muted">{projects.length}개</span>
      </div>

      <section className="grid grid3">
        {projects.length ? (
          projects.map((project: any) => (
            <article className="card projectCard" key={project.id}>
              <div className="cardTopline">
                <span
                  className={`badge ${project.status === 'ready' || project.status === 'complete' ? 'badgeReady' : ''}`}
                >
                  {project.status}
                </span>
                <ProjectDeleteButton
                  projectId={project.id}
                  projectName={project.name}
                />
              </div>
              <h3>{project.name}</h3>
              <p className="muted">
                {project.family_name} · {project.glyph_count}자
              </p>
              <div className="progress">
                <span style={{ width: `${project.progress}%` }} />
              </div>
              <p>
                <Link href={`/projects/${project.id}`}>프로젝트 열기 →</Link>
              </p>
            </article>
          ))
        ) : (
          <article className="card">
            <h3>첫 프로젝트를 만드십시오.</h3>
            <p className="muted">새 프로젝트 버튼으로 작업을 시작할 수 있습니다.</p>
          </article>
        )}
      </section>
    </main>
  );
}
