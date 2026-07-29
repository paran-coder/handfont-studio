export function TemplateDownloads() {
  return (
    <div className="downloadActions" aria-label="손글씨 작성 양식 다운로드">
      <a
        className="button buttonAccent"
        href="/templates/handfont-writing-template.pdf"
        download
      >
        작성 양식 PDF
      </a>
      <a
        className="button buttonSoft"
        href="/templates/handfont-writing-template-png.zip"
        download
      >
        PNG 묶음
      </a>
    </div>
  );
}
