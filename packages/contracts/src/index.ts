export type JobKind = 'process' | 'export';
export type JobStatus = 'queued' | 'leased' | 'running' | 'complete' | 'failed';
export type ProjectStep = 'upload' | 'review' | 'style' | 'preview' | 'export';
export type ProjectStatus = 'draft' | 'processing' | 'ready' | 'complete';
export type GlyphStatus = 'ok' | 'review' | 'missing';

export interface StyleSettings {
  weight: number;
  width: number;
  slant: number;
  roundness: number;
  spacing: number;
  lineHeight: number;
}

export interface QueueMessage {
  schemaVersion: '3.3.0';
  jobId: string;
  projectId: string;
  kind: JobKind;
  idempotencyKey: string;
  callbackBaseUrl: string;
}

export interface WorkerProgress {
  progress: number;
  message: string;
  stage?: string;
}

export interface GlyphResult {
  page: number;
  cellId: string;
  character: string;
  unicode: string;
  status: GlyphStatus;
  rawIou: number;
  tolerantF1: number;
  inkRatio: number;
  svgUrl: string;
  metadataUrl: string;
}
