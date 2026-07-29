import {getJob} from '@/lib/repository';import {jsonError} from '@/lib/security';
export async function GET(_:Request,{params}:{params:Promise<{jobId:string}>}){const {jobId}=await params;const job=await getJob(jobId);return job?Response.json(job):jsonError('작업을 찾을 수 없습니다.',404)}
