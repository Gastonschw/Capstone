-- Sync new sign-ups from auth.users into public.users (e.g. Google login).
-- Run this in Supabase SQL Editor. Requires public.users to exist.

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = ''
as $$
begin
  insert into public.users (id, email, full_name, avatar_url)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'name'),
    new.raw_user_meta_data->>'avatar_url'
  )
  on conflict (id) do update set
    email = excluded.email,
    full_name = coalesce(excluded.full_name, public.users.full_name),
    avatar_url = coalesce(excluded.avatar_url, public.users.avatar_url),
    updated_at = now();
  return new;
end;
$$;

-- Trigger: run after every insert into auth.users (sign-up / first Google login)
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- Optional: backfill public.users for users who already exist in auth.users (run once)
insert into public.users (id, email, full_name, avatar_url)
select
  id,
  email,
  coalesce(raw_user_meta_data->>'full_name', raw_user_meta_data->>'name'),
  raw_user_meta_data->>'avatar_url'
from auth.users
on conflict (id) do update set
  email = excluded.email,
  full_name = coalesce(excluded.full_name, public.users.full_name),
  avatar_url = coalesce(excluded.avatar_url, public.users.avatar_url),
  updated_at = now();
