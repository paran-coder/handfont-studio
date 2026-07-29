'use client';
import { useState } from 'react';
import { upload } from '@vercel/blob/client';
import { useRouter } from 'next/navigation';
export function UploadClient({projectId}:{projectId:string}){
 const [progress,setProgress]=useState(0);const [busy,setBusy]=useState(false);const [message,setMessage]=useState('');const router=useRouter();
 async function submit(files:FileList|null){if(!files?.length)return;setBusy(true);setMessage('업로드 중');try{for(const file of Array.from(files)){if(process.env.NEXT_PUBLIC_STORAGE_DRIVER==='local'){const body=new FormData();body.append('projectId',projectId);body.append('file',file);const res=await fetch('/api/uploads/local',{method:'POST',body});if(!res.ok)throw new Error(await res.text());}else{await upload(`projects/${projectId}/uploads/${file.name}`,file,{access:'private',handleUploadUrl:'/api/uploads/token',clientPayload:JSON.stringify({projectId,originalName:file.name,contentType:file.type,size:file.size}),onUploadProgress:e=>setProgress(Math.round(e.percentage))});}}setMessage('업로드 완료');router.refresh();}catch(e){setMessage(e instanceof Error?e.message:'업로드 실패')}finally{setBusy(false)}}
 return <div className="uploadBox"><h3>작성본 파일 업로드</h3><p className="muted">JPG, PNG, WEBP, PDF · 파일당 최대 25MB</p><input type="file" multiple accept=".jpg,.jpeg,.png,.webp,.pdf" disabled={busy} onChange={e=>submit(e.target.files)}/>{busy&&<><div className="progress" style={{marginTop:18}}><span style={{width:`${progress}%`}}/></div><p>{progress}%</p></>}<p>{message}</p></div>
}
