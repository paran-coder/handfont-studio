declare const process: { env: Record<string, string | undefined> };
declare const Buffer: { from(value: string | ArrayBuffer): any };
declare module 'react' {
  export type ReactNode = any;
  export function useState<T>(value: T): [T, (value: T) => void];
}
declare namespace React { type ReactNode = any; }
declare namespace JSX { interface IntrinsicElements { [elemName: string]: any } }
declare module 'next/link' { const Link: any; export default Link; }
declare module 'next/navigation' {
  export function notFound(): never;
  export function redirect(path: string): never;
  export function useRouter(): { refresh(): void };
}
declare module 'postgres' { const postgres: any; export default postgres; }
declare module '@vercel/queue' { export function send(topic: string, message: any): Promise<{messageId:string}>; }
declare module '@vercel/blob/client' {
  export type HandleUploadBody = any;
  export function upload(pathname:string,file:File,options:any):Promise<any>;
  export function handleUpload(options:any):Promise<any>;
}
declare module '@vercel/blob' { export function get(url:string,options:any):Promise<any>; }
declare module 'node:crypto' { export function randomUUID(): string; export function timingSafeEqual(a:any,b:any): boolean; }
declare module 'node:fs/promises' { export function mkdir(...args:any[]):Promise<any>; export function writeFile(...args:any[]):Promise<any>; export function readFile(...args:any[]):Promise<any>; }
declare module 'node:path' { const path:any; export default path; }
