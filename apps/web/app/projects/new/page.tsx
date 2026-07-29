import { redirect } from 'next/navigation';
import { requireOwnerId } from '@/lib/owner';
import { createProject } from '@/lib/repository';

async function action(formData: FormData) {
  'use server';
  const name = String(formData.get('name') || '').trim();
  const familyName = String(formData.get('familyName') || '').trim();
  if (!name || !familyName) return;
  const ownerId = await requireOwnerId();
  const project: any = await createProject(ownerId, {
    name,
    familyName,
    description: String(formData.get('description') || ''),
  });
  redirect(`/projects/${project.id}`);
}

export default function NewProject() {
  return (
    <main className="page">
      <h1>새 폰트 프로젝트</h1>
      <p className="muted">
        폰트 이름은 내보내는 TTF의 family name으로 사용됩니다. 프로젝트는 현재
        브라우저에만 연결됩니다.
      </p>
      <form action={action} className="card form">
        <label>
          프로젝트 이름
          <input className="input" name="name" required maxLength={80} />
        </label>
        <label>
          폰트 패밀리 이름
          <input className="input" name="familyName" required maxLength={80} />
        </label>
        <label>
          설명
          <textarea className="input" name="description" rows={4} />
        </label>
        <button className="button buttonAccent">프로젝트 생성</button>
      </form>
    </main>
  );
}
