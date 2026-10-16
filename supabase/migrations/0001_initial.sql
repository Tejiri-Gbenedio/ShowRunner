create table if not exists pipeline_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  state text not null default 'draft',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists pipeline_runs_user_id_idx on pipeline_runs(user_id);

alter table pipeline_runs enable row level security;
