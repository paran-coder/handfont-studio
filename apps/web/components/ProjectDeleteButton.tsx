'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export function ProjectDeleteButton({
  projectId,
  projectName,
  redirectHome = false,
}: {
  projectId: string;
  projectName: string;
  redirectHome?: boolean;
}) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const router = useRouter();

  async function remove() {
    const confirmed = window.confirm(
      `“${projectName}” 프로젝트와 업로드 파일, 글리프, 완성 폰트를 모두 삭제하시겠습니까?\n\n삭제한 프로젝트는 복구할 수 없습니다.`,
    );
    if (!confirmed) return;

    setBusy(true);
    setMessage('');
    try {
      const response = await fetch(`/api/projects/${projectId}`, {
        method: 'DELETE',
      });
      const data = (await response.json()) as { detail?: string };
      if (!response.ok) {
        setMessage(data.detail ?? '프로젝트 삭제에 실패했습니다.');
        return;
      }
      if (redirectHome) {
        router.push('/');
      }
      router.refresh();
    } catch {
      setMessage('네트워크 오류로 프로젝트를 삭제하지 못했습니다.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="deleteControl">
      <button className="button buttonDanger" disabled={busy} onClick={remove}>
        {busy ? '삭제 중…' : '프로젝트 삭제'}
      </button>
      {message ? <p className="errorText">{message}</p> : null}
    </div>
  );
}
