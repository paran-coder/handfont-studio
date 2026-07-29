import './globals.css';
import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'HandFont Studio',
  description: '손글씨를 폰트로 만드는 웹 서비스',
  openGraph: {
    title: 'HandFont Studio',
    description: '손글씨를 폰트로 만드는 웹 서비스',
    type: 'website',
    locale: 'ko_KR',
    siteName: 'HandFont Studio',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'HandFont Studio',
    description: '손글씨를 폰트로 만드는 웹 서비스',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <div className="shell">
          <aside className="sidebar">
            <Link className="brand" href="/">
              <span className="brandMark">H</span>
              <span>
                HandFont Studio
                <small>Cloud Web · v3.3.6</small>
              </span>
            </Link>
            <nav className="nav">
              <Link href="/">프로젝트</Link>
              <Link href="/projects/new">새 프로젝트</Link>
              <Link href="/deploy">배포 상태</Link>
            </nav>
          </aside>
          <div className="main">
            <header className="topbar">
              <strong>손글씨 폰트 제작 스튜디오</strong>
              <span className="badge badgeReady">Vercel Ready</span>
            </header>
            {children}
          </div>
        </div>
      </body>
    </html>
  );
}
