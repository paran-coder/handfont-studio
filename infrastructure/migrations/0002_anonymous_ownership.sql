-- v3.3.6: browser-scoped anonymous ownership
-- Existing owner_id='anonymous' rows are intentionally not reassigned.

alter table projects alter column owner_id drop default;

create index if not exists projects_owner_updated_idx
  on projects(owner_id, updated_at desc);
