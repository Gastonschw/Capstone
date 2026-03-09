-- Add role to public.users and create classes / class_members tables.
-- Run this in Supabase SQL Editor or via Supabase migrations.

-- 1. Add role column to public.users
alter table public.users
  add column if not exists role text not null default 'general';

-- Ensure role is one of the expected values
alter table public.users
  drop constraint if exists users_role_check;

alter table public.users
  add constraint users_role_check
  check (role in ('admin', 'general'));


-- 2. Classes table (owned by a teacher/admin)
create table if not exists public.classes (
  id uuid not null default gen_random_uuid() primary key,
  name text not null,
  description text,
  owner_user_id uuid not null references public.users (id) on delete cascade,
  join_code text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists idx_classes_join_code
  on public.classes (join_code);

create index if not exists idx_classes_owner_user_id
  on public.classes (owner_user_id);

-- Keep updated_at fresh on update if helper exists
do $$
begin
  if exists (
    select 1
    from pg_proc
    join pg_namespace n on n.oid = pg_proc.pronamespace
    where n.nspname = 'public'
      and pg_proc.proname = 'set_current_timestamp'
  ) then
    drop trigger if exists set_current_timestamp_on_classes on public.classes;

    create trigger set_current_timestamp_on_classes
      before update on public.classes
      for each row execute procedure public.set_current_timestamp();
  end if;
end;
$$;


-- 3. Class membership table (students in classes)
create table if not exists public.class_members (
  id uuid not null default gen_random_uuid() primary key,
  class_id uuid not null references public.classes (id) on delete cascade,
  user_id uuid not null references public.users (id) on delete cascade,
  created_at timestamptz not null default now(),
  unique (class_id, user_id)
);

create index if not exists idx_class_members_user_id
  on public.class_members (user_id);

