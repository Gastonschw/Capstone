# Supabase setup (users + GitHub linking)

## 1. Supabase project

- Create a project at [supabase.com](https://supabase.com) if you haven’t.
- Ensure **Authentication → Providers → Google** is enabled and your Google OAuth client ID/secret are set (use the same redirect URL Supabase shows).
- Create the `public.users` table (id uuid PK references auth.users(id) on delete cascade, created_at, updated_at, email, full_name, avatar_url).

## 2. Run the migrations

In the [Supabase SQL Editor](https://supabase.com/dashboard/project/_/sql), run in order:

1. **`migrations/20260217100000_sync_auth_users_to_public_users.sql`**  
   Adds a trigger so that **every new sign-up** (e.g. Google login) inserts a row into `public.users`. Also backfills existing `auth.users` into `public.users`. Without this, Google login does **not** add to `public.users`.

2. **`migrations/20260217000000_link_users_repos_github_tokens.sql`**  
   Adds `owner_user_id` to `repositories`, `user_id` to `github_tokens`, and the `set_current_timestamp()` trigger function.

## 3. Frontend env

In `combined-analyzer/frontend`, copy `.env.example` to `.env` and set:

- `VITE_SUPABASE_URL` – Project URL (Dashboard → Project Settings → API)
- `VITE_SUPABASE_ANON_KEY` – anon/public key

If these are not set, the app still runs; the “Sign in with Google” block in the header is hidden.

## 4. What’s wired

- **Header:** “Sign in with Google” and “Sign out” when Supabase env vars are set. On sign-in, the session user id is stored and sent as `X-User-Id` on all API requests.
- **Repos:** List, upload, and GitHub import use `X-User-Id` so data is scoped to the signed-in user.
- **GitHub connect:** When the user starts GitHub OAuth while signed in, the token is linked to that user via `user_id` in the OAuth state.

No backend code changes are required beyond the migration and your existing backend support for `X-User-Id` and `user_id` in the GitHub callback.
