-- Run transactionally after ORM table creation and the earlier identity migrations.
-- Existing analyses intentionally retain NULL snapshots: their original selection
-- cannot be reconstructed honestly, so chat requires a new run.
do $$
declare
  table_name text;
  constraint_name text;
  role_name text;
begin
  foreach table_name in array array[
    'erd_analyses', 'integrity_analyses', 'compliance_analyses',
    'correctness_analyses', 'usability_analyses', 'maintainability_analyses'
  ] loop
    execute format('alter table public.%I add column if not exists selected_files json', table_name);
  end loop;

  -- ORM cascades do not participate in auth.users -> users database cascades.
  foreach table_name in array array[
    'discovered_files', 'erd_analyses', 'integrity_analyses', 'compliance_analyses',
    'correctness_analyses', 'usability_analyses', 'maintainability_analyses'
  ] loop
    for constraint_name in
      select c.conname from pg_constraint c
      join pg_attribute a on a.attrelid = c.conrelid and a.attnum = any(c.conkey)
      where c.conrelid = format('public.%I', table_name)::regclass
        and c.contype = 'f' and a.attname = 'repository_id'
    loop
      execute format('alter table public.%I drop constraint %I', table_name, constraint_name);
    end loop;
    execute format('alter table public.%I add constraint %I foreign key (repository_id) references public.repositories(id) on delete cascade', table_name, table_name || '_repository_id_fkey');
  end loop;

  foreach table_name in array array['class_members', 'class_admins'] loop
    for constraint_name in
      select c.conname from pg_constraint c
      join pg_attribute a on a.attrelid = c.conrelid and a.attnum = any(c.conkey)
      where c.conrelid = format('public.%I', table_name)::regclass
        and c.contype = 'f' and a.attname in ('class_id', 'user_id')
    loop
      execute format('alter table public.%I drop constraint %I', table_name, constraint_name);
    end loop;
    execute format('alter table public.%I add constraint %I foreign key (class_id) references public.classes(id) on delete cascade', table_name, table_name || '_class_id_fkey');
    execute format('alter table public.%I add constraint %I foreign key (user_id) references public.users(id) on delete cascade not valid', table_name, table_name || '_user_id_fkey');
  end loop;

  alter table public.classes drop constraint if exists classes_owner_user_id_fkey;
  alter table public.classes add constraint classes_owner_user_id_fkey
    foreign key (owner_user_id) references public.users(id) on delete cascade;

  -- Legacy unowned credentials cannot be safely attributed to an authenticated user.
  delete from public.github_tokens where user_id is null;
  alter table public.github_tokens alter column user_id set not null;

  foreach table_name in array array['github_oauth_states', 'github_oauth_tickets'] loop
    execute format('alter table public.%I add constraint %I foreign key (user_id) references public.users(id) on delete cascade', table_name, table_name || '_user_id_fkey');
  end loop;

  -- These tables are accessed only through the verified FastAPI authorization layer.
  -- The database connection must be an owner/BYPASSRLS role, never an anon key.
  foreach table_name in array array[
    'users', 'repositories', 'discovered_files', 'github_tokens',
    'github_oauth_states', 'github_oauth_tickets', 'classes', 'class_members', 'class_admins',
    'erd_analyses', 'integrity_analyses', 'compliance_analyses',
    'correctness_analyses', 'usability_analyses', 'maintainability_analyses',
    'application_schema_migrations'
  ] loop
    execute format('alter table public.%I enable row level security', table_name);
    execute format('revoke all on table public.%I from public', table_name);
    foreach role_name in array array['anon', 'authenticated'] loop
      if exists (select 1 from pg_roles where rolname = role_name) then
        execute format('revoke all on table public.%I from %I', table_name, role_name);
      end if;
    end loop;
  end loop;
end;
$$;

-- The checklist is the only application table intentionally exposed directly.
create table if not exists public.user_checklists (
  user_id uuid primary key references public.users(id) on delete cascade,
  items jsonb not null default '[]'::jsonb check (jsonb_typeof(items) = 'array')
);
alter table public.user_checklists enable row level security;
revoke all on table public.user_checklists from public;
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    revoke all on table public.user_checklists from anon;
  end if;
  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    revoke all on table public.user_checklists from authenticated;
    grant select, insert, update, delete on public.user_checklists to authenticated;
  end if;
end;
$$;
drop policy if exists own_checklist on public.user_checklists;
create policy own_checklist on public.user_checklists
  for all to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);
