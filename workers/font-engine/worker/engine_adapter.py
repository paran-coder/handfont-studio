from __future__ import annotations
import hashlib,json,re,shutil,sys,zipfile
from pathlib import Path
from typing import Any,Callable
import cv2,fitz,numpy as np
from .storage import Storage
SERVICE_ROOT=Path(__file__).resolve().parents[1]/'engine'/'services'
for name in ('capture-ingest','image-pipeline','glyph-vectorizer','hangul-engine','hangul-composer','font-builder','orchestrator'):
    p=str(SERVICE_ROOT/name)
    if p not in sys.path: sys.path.insert(0,p)
Progress=Callable[[int,str],None]
def _safe(v:str)->str: return re.sub(r'[^A-Za-z0-9가-힣._-]+','-',v.strip()).strip('-._') or 'HandFont'
def _sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def _f1(a:Path,b:Path,tolerance:int=1)->float:
    x=cv2.imread(str(a),cv2.IMREAD_GRAYSCALE);y=cv2.imread(str(b),cv2.IMREAD_GRAYSCALE)
    if x is None or y is None:return 0.0
    xm=x>0;ym=y>0
    if not xm.any() or not ym.any():return 0.0
    k=np.ones((tolerance*2+1,tolerance*2+1),np.uint8)
    p=float((ym & cv2.dilate(xm.astype(np.uint8),k).astype(bool)).sum())/float(ym.sum())
    r=float((xm & cv2.dilate(ym.astype(np.uint8),k).astype(bool)).sum())/float(xm.sum())
    return 0.0 if p+r==0 else 2*p*r/(p+r)
def _prepare(paths:list[Path],target:Path)->list[Path]:
    target.mkdir(parents=True,exist_ok=True);out=[]
    for path in paths:
        if path.suffix.lower()!='.pdf':out.append(path);continue
        doc=fitz.open(path)
        try:
            for i,page in enumerate(doc):
                dest=target/f'{path.stem}-page-{i+1:02d}.png';page.get_pixmap(dpi=170,alpha=False).save(dest);out.append(dest)
        finally:doc.close()
    return out
def process(manifest:dict[str,Any],storage:Storage,work:Path,progress:Progress)->tuple[dict[str,Any],list[dict[str,Any]]]:
    from handfont_capture.models import SessionOptions
    from handfont_capture.session import process_capture_session
    project=manifest['project'];uploads=manifest['uploads'];input_dir=work/'inputs';prepared_dir=work/'prepared';run_dir=work/'processing'
    shutil.rmtree(work,ignore_errors=True);input_dir.mkdir(parents=True);run_dir.mkdir(parents=True)
    progress(5,'입력 Blob을 내려받고 있습니다.')
    paths=[]
    for i,u in enumerate(uploads,1):
        suffix=Path(u['original_name']).suffix or '.bin';paths.append(storage.download(u['blob_url'],input_dir/f'{i:02d}{suffix}'))
    prepared=_prepare(paths,prepared_dir);progress(14,'등록 마커와 페이지를 식별하고 있습니다.')
    summary=process_capture_session(prepared,run_dir,SessionOptions(dpi=150,expected_pages=tuple(),vectorize=True,vectorize_limit=None))
    if not summary.get('selected_pages'):raise RuntimeError('식별된 작성 페이지가 없습니다.')
    if summary.get('failed_inputs'):raise RuntimeError(f"처리 실패 입력: {summary.get('failures')}")
    progress(72,'SVG 글리프를 객체 저장소에 업로드하고 있습니다.')
    vector_by_cell={r['cell_id']:r for r in summary.get('vectorization',{}).get('records',[])};glyphs=[];project_id=project['id']
    for page in summary.get('selected_pages',[]):
        meta=json.loads((run_dir/'pages'/f'page-{int(page):02d}'/'metadata.json').read_text(encoding='utf-8'))
        for cell in meta.get('cells',[]):
            rec=vector_by_cell.get(cell['cell_id'])
            if not rec:continue
            source=(run_dir/rec['svg']).parent;vmeta=json.loads((source/'metadata.json').read_text(encoding='utf-8'))
            raw=float(vmeta.get('summary',{}).get('raster_iou',rec.get('raster_iou',0)));f1=_f1(source/'original-mask.png',source/'vector-raster.png')
            status='ok' if cell.get('quality',{}).get('status')=='ok' and f1>=.98 else 'review';prefix=f'projects/{project_id}/glyphs/{cell["cell_id"]}'
            svg_url=storage.upload(source/'glyph.svg',f'{prefix}/glyph.svg','image/svg+xml');meta_url=storage.upload(source/'metadata.json',f'{prefix}/metadata.json','application/json')
            glyphs.append({'page':int(page),'cellId':cell['cell_id'],'character':cell.get('character',''),'unicode':cell.get('unicode',''),'status':status,'rawIou':round(raw,6),'tolerantF1':round(f1,6),'inkRatio':float(cell.get('quality',{}).get('ink_ratio',0)),'svgUrl':svg_url,'metadataUrl':meta_url})
    if not glyphs:raise RuntimeError('벡터화된 글리프가 없습니다.')
    overview=None
    if (run_dir/'capture-overview.png').exists():overview=storage.upload(run_dir/'capture-overview.png',f'projects/{project_id}/reports/capture-overview.png','image/png')
    result={'engine':'capture-ingest-v1.8+vectorizer-v1.4','selected_pages':summary.get('selected_pages',[]),'glyph_count':len(glyphs),'review_count':sum(g['status']!='ok' for g in glyphs),'mean_raw_iou':round(sum(g['rawIou'] for g in glyphs)/len(glyphs),6),'mean_tolerant_f1':round(sum(g['tolerantF1'] for g in glyphs)/len(glyphs),6),'capture_overview_url':overview}
    progress(98,'분석 결과를 저장하고 있습니다.');return result,glyphs
def export(manifest:dict[str,Any],storage:Storage,work:Path,progress:Progress)->tuple[dict[str,Any],str]:
    from handfont_fontbuilder.builder import build_font
    from handfont_fontbuilder.models import FontBuildOptions
    from handfont_fontbuilder.validation import validate_and_render
    shutil.rmtree(work,ignore_errors=True);work.mkdir(parents=True);project=manifest['project'];glyphs=[g for g in manifest['glyphs'] if g['status']!='missing'];items=[]
    progress(8,'SVG 글리프를 내려받고 있습니다.')
    for i,g in enumerate(glyphs):
        d=work/'glyphs'/g['cell_id'];svg=storage.download(g['svg_url'],d/'glyph.svg');meta=storage.download(g['metadata_url'],d/'metadata.json');items.append({'character':g['character'],'codepoint':ord(g['character']),'category':'web-captured','cell_id':g['cell_id'],'svg':str(svg),'metadata':str(meta)})
    if not items:raise RuntimeError('내보낼 글리프가 없습니다.')
    manifest_path=work/'glyph-manifest.json';manifest_path.write_text(json.dumps({'schema_version':'3.3.0','source_type':'cloud-web','glyphs':items},ensure_ascii=False,indent=2),encoding='utf-8')
    progress(35,'TrueType 폰트를 빌드하고 있습니다.');basename=_safe(project['family_name'])+'-Regular';report=build_font(manifest_path,work,FontBuildOptions(family_name=project['family_name'],style_name='Regular',version='3.3.1',output_basename=basename));font=work/report['font']
    progress(68,'폰트 테이블과 렌더링을 검증하고 있습니다.');validation=validate_and_render(font,work);violations=len(report.get('missing_tables',[]))+len(report.get('bounds_violations',[]))+len(validation.get('empty_outlines',[]))+len(validation.get('metric_violations',[]))+len(validation.get('hangul_width_violations',[]))+len(validation.get('empty_rendered_glyphs',[]))
    if violations:raise RuntimeError(f'폰트 검증 위반 {violations}건')
    package=work/f'{basename}-cloud-export.zip'
    with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
        for n in (report['font'],'font-build-report.json','font-validation.json','glyph-metrics.csv','font-specimen.png','glyph-grid.png',f"{report['font']}.sha256"):
            p=work/n
            if p.exists():z.write(p,n)
    prefix=f"projects/{project['id']}/exports/{manifest['job']['id']}";artifact=storage.upload(package,f'{prefix}/{package.name}','application/zip')
    specimen=storage.upload(work/'font-specimen.png',f'{prefix}/font-specimen.png','image/png') if (work/'font-specimen.png').exists() else None
    result={'engine':'font-builder-v1.6','glyph_count':len(items),'font_glyph_count':report.get('glyph_count'),'cmap_count':validation.get('cmap_count'),'hangul_cmap_count':validation.get('hangul_cmap_count'),'validation_violations':violations,'font_sha256':_sha(font),'package_sha256':_sha(package),'artifact_url':artifact,'specimen_url':specimen}
    progress(98,'내보내기 결과를 업로드했습니다.');return result,artifact
