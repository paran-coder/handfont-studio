create table if not exists projects (
  id text primary key,
  owner_id text not null default 'anonymous',
  name text not null,
  family_name text not null,
  description text not null default '',
  current_step text not null default 'upload' check (current_step in ('upload','review','style','preview','export')),
  status text not null default 'draft' check (status in ('draft','processing','ready','complete')),
  progress integer not null default 0 check (progress between 0 and 100),
  glyph_count integer not null default 0,
  review_count integer not null default 0,
  style jsonb not null default '{"weight":0,"width":100,"slant":0,"roundness":0,"spacing":0,"lineHeight":150}',
  preview_text text not null default '안녕하세요. 나만의 손글씨 폰트입니다.',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists uploads (
  id text primary key,
  project_id text not null references projects(id) on delete cascade,
  original_name text not null,
  pathname text not null unique,
  blob_url text not null,
  content_type text not null,
  size bigint not null check (size >= 0),
  status text not null default 'uploaded' check (status in ('uploaded','processing','processed','failed')),
  created_at timestamptz not null default now()
);
create table if not exists glyphs (
  id bigserial primary key,
  project_id text not null references projects(id) on delete cascade,
  page integer not null check (page between 1 and 99),
  cell_id text not null,
  character text not null,
  unicode text not null,
  status text not null default 'ok' check (status in ('ok','review','missing')),
  raw_iou double precision not null default 0,
  tolerant_f1 double precision not null default 0,
  ink_ratio double precision not null default 0,
  svg_url text not null,
  metadata_url text not null,
  unique(project_id,cell_id)
);
create table if not exists jobs (
  id text primary key,
  project_id text not null references projects(id) on delete cascade,
  kind text not null check (kind in ('process','export')),
  status text not null default 'queued' check (status in ('queued','leased','running','complete','failed')),
  progress integer not null default 0 check (progress between 0 and 100),
  message text not null default '',
  payload jsonb not null default '{}',
  result jsonb not null default '{}',
  artifact_url text,
  error text,
  lease_token text,
  attempts integer not null default 0,
  idempotency_key text not null unique,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists glyphs_project_page_idx on glyphs(project_id,page);
create index if not exists glyphs_project_status_idx on glyphs(project_id,status);
create index if not exists jobs_status_created_idx on jobs(status,created_at);
create index if not exists uploads_project_idx on uploads(project_id,created_at);
