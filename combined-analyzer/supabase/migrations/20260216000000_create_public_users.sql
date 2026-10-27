-- Application identity is backed by Supabase Auth, never a client-supplied UUID.
do $$
begin
  if to_regclass('auth.users') is null then
    raise exception 'Supabase auth.users is required before application migrations';
  end if;
end;
$$;

create table if not exists public.users (
  id uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  email text,
  full_name text,
  avatar_url text
);
