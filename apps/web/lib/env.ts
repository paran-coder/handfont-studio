const required = (name: string, fallback?: string): string => {
  const value = process.env[name] ?? fallback;
  if (!value) throw new Error(`필수 환경변수가 없습니다: ${name}`);
  return value;
};

const withHttps = (value: string): string =>
  /^https?:\/\//.test(value) ? value : `https://${value}`;

const resolveAppBaseUrl = (): string => {
  const explicit = process.env.APP_BASE_URL;
  if (explicit) return explicit.replace(/\/$/, '');
  const production = process.env.VERCEL_PROJECT_PRODUCTION_URL;
  if (production) return withHttps(production).replace(/\/$/, '');
  const deployment = process.env.VERCEL_URL;
  if (deployment) return withHttps(deployment).replace(/\/$/, '');
  return 'http://localhost:3000';
};

export const env = {
  databaseUrl: required('DATABASE_URL'),
  appBaseUrl: resolveAppBaseUrl(),
  workerSecret: required('WORKER_SHARED_SECRET'),
  storageDriver: process.env.STORAGE_DRIVER ?? 'local',
  localBlobDir: process.env.LOCAL_BLOB_DIR ?? '../../runtime/blob',
  queueDriver: process.env.QUEUE_DRIVER ?? 'local',
  queueTopic: process.env.VERCEL_QUEUE_TOPIC ?? 'handfont-jobs',
  queueRegion: process.env.VERCEL_QUEUE_REGION ?? 'icn1',
  maxUploadBytes: Number(process.env.MAX_UPLOAD_BYTES ?? 25 * 1024 * 1024),
};
