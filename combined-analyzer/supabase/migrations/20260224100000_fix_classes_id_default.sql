-- Ensure classes and class_members ids use server-side UUID defaults.

alter table public.classes
  alter column id set default gen_random_uuid();

alter table public.class_members
  alter column id set default gen_random_uuid();

