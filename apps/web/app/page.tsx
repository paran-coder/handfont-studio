import Link from 'next/link';
import { listProjects } from '@/lib/repository';
export const dynamic='force-dynamic';
export default async function Home(){
 let projects:any[]=[]; try{projects=await listProjects() as any[]}catch{}
 return <main className="page"><section className="hero"><div><p style={{color:'#f06f4f',fontWeight:800}}>HANDFONT CLOUD</p><h1>내 손글씨를<br/>설치 가능한 폰트로.</h1><p>작성본은 객체 저장소로 직접 업로드되고, 독립 워커가 페이지 보정·SVG 벡터화·TTF 생성을 처리합니다.</p><div style={{display:'flex',gap:10}}><Link className="button buttonAccent" href="/projects/new">새 프로젝트</Link><Link className="button buttonSoft" href="/deploy">배포 준비 보기</Link></div></div><div className="paper">가나다<br/>ABC 123</div></section><div className="sectionHead"><h2>프로젝트</h2><span className="muted">{projects.length}개</span></div><section className="grid grid3">{projects.length?projects.map((p:any)=><article className="card" key={p.id}><span className={`badge ${p.status==='ready'?'badgeReady':''}`}>{p.status}</span><h3>{p.name}</h3><p className="muted">{p.family_name} · {p.glyph_count}자</p><div className="progress"><span style={{width:`${p.progress}%`}}/></div><p><Link href={`/projects/${p.id}`}>프로젝트 열기 →</Link></p></article>):<article className="card"><h3>첫 프로젝트를 만드십시오.</h3><p className="muted">PostgreSQL 연결 후 여기에 작업이 저장됩니다.</p></article>}</section></main>;
}
