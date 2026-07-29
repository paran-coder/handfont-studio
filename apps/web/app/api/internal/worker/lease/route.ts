import {leaseNextJob} from '@/lib/repository';import {requireWorker,jsonError} from '@/lib/security';
export async function POST(request:Request){try{requireWorker(request);const job=await leaseNextJob();return Response.json({job})}catch(e){return jsonError(e instanceof Error&&e.message==='WORKER_UNAUTHORIZED'?'인증 실패':'작업 임대 실패',e instanceof Error&&e.message==='WORKER_UNAUTHORIZED'?401:500)}}
