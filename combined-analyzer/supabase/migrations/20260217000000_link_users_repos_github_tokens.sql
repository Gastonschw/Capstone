-- Link repositories and github_tokens to public.users (Google Auth).
-- Run this in Supabase SQL Editor after public.users exists and set_current_timestamp exists.
-- 1. Ensure trigger function exists
create or replace function public.set_current_timestamp()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

-- 2. Add owner_user_id to repositories (run in two steps to avoid timeout)
alter table public.repositories
  add column if not exists owner_user_id uuid;

alter table public.repositories
  drop constraint if exists repositories_owner_user_id_fkey;

alter table public.repositories
  add constraint repositories_owner_user_id_fkey
  foreign key (owner_user_id)
  references public.users (id)
  on delete cascade;

-- 3. Add user_id to github_tokens
alter table public.github_tokens
  add column if not exists user_id uuid;

alter table public.github_tokens
  drop constraint if exists github_tokens_user_id_fkey;

alter table public.github_tokens
  add constraint github_tokens_user_id_fkey
  foreign key (user_id)
  references public.users (id)
  on delete cascade;

-- Optional: index for filtering repos by owner
create index if not exists idx_repositories_owner_user_id
  on public.repositories (owner_user_id);

-- Optional: index for looking up token by user
create index if not exists idx_github_tokens_user_id
  on public.github_tokens (user_id);
