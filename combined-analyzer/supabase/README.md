# Supabase setup and schema upgrades

## Project and authentication

1. Create a Supabase project. Its `auth.users`, `auth.uid()`, `anon`, and `authenticated` roles/functions must exist before application startup.
2. Enable Google under Authentication → Providers and configure the Google client credentials.
3. Add the frontend origin and its `/analyzer` URL to allowed redirects.
4. Set backend `DATABASE_URL`, `SUPABASE_URL`, and `SUPABASE_ANON_KEY`; set frontend `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` to the same project's public values.
5. Supply the other required backend configuration in the [application README](../README.md), particularly the persistent token encryption key.

The backend verifies each bearer token against this project's `/auth/v1/user`. UUID headers are not accepted. Do not place a service-role key or PostgreSQL password in any `VITE_*` variable.

## Complete ordered migration sequence

Backend startup acquires a migration lock, bootstraps `public.users`, creates registered ORM tables, and then applies the following SQL files transactionally. Applied filenames are tracked in `public.application_schema_migrations`; do not edit an applied file to perform a future upgrade—add a new migration.

1. `20260216000000_create_public_users.sql`: creates the application identity profile linked to `auth.users`.
2. ORM table creation: repositories, discoveries, six report types, GitHub credentials/tickets/states, classes, memberships, and additional administrators.
3. `20260217000000_link_users_repos_github_tokens.sql`: ownership foreign keys and timestamp helper.
4. `20260217100000_sync_auth_users_to_public_users.sql`: sign-up trigger and existing-user backfill.
5. `20260224090000_add_user_roles_and_classes.sql`: role column/constraint, classroom indexes and update trigger.
6. `20260224100000_fix_classes_id_default.sql`: server-side UUID defaults.
7. `20261027000000_secure_application_tables.sql`: immutable analysis selection columns, cascading relationship constraints, required token ownership, private backend-table grants/RLS, and owner-only checklist access.

The application will not serve traffic if any step fails. Existing manually applied historical migrations are idempotent and can be recorded by the first managed startup. Back up before upgrades. Ownerless GitHub credentials are deliberately removed; ownerless repository data is preserved for administrative review. Legacy reports keep NULL input snapshots rather than fabricated history.

Do not run only the old two-file subset from previous setup instructions. Creating ORM tables alone does not add columns or replace constraints in existing tables.

## Administrator assignment

New users receive `role='general'`. After the intended teacher signs in, a trusted database administrator can grant the global class-creation role:

```sql
update public.users
set role = 'admin'
where id = 'the-teachers-verified-auth-uuid';
```

Never expose general role updates through the frontend. Class-scoped promotion creates a `class_admins` entry, not a global role change. Both creators and additional class administrators are recognized for student-run inspection and application routing.

## Data API boundaries

The frontend accesses only `public.user_checklists` directly. Its RLS policy requires `auth.uid() = user_id` for reads and writes, and only the authenticated role has table grants.

Repositories, analyses, user profiles, GitHub credentials/state/tickets, classroom tables, and the migration journal have RLS enabled and no `anon`/`authenticated` table grants. They are accessed through FastAPI after bearer verification and ownership/class checks. The backend PostgreSQL connection must use a trusted owner/BYPASSRLS role; it must not be an API anon role.

The hardening migration revokes direct client access to these application tables even if previous project defaults granted it. Review any separately maintained custom policies and integrations before upgrading.

## Account and storage lifecycle

Deleting a Supabase auth account cascades profile, owned repository/report/discovery records, classes, memberships, and credentials. ORM and database cascades agree, including additional class administrators. Database-originated deletion cannot remove filesystem directories: record affected `repositories.local_path` values before administrative account deletion and remove those directories from persistent storage afterward.

Archive imports and normal repository deletion are handled by the backend. Keep database and persistent-file backups together. Metadata and 500-character previews are not a repository backup.
