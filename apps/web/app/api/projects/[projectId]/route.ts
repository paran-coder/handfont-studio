import {getProject,listUploads} from '@/lib/repository';import {jsonError} from '@/lib/security';
export async function GET(_:Request,{params}:{params:Promise<{projectId:string}>}){const {projectId}=await params;const p=await getProject(projectId);if(!p)return jsonError('프로젝트를 찾을 수 없습니다.',404);return Response.json({...p,uploads:await listUploads(projectId)})}
