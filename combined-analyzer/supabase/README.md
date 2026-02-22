# Supabase setup (users + GitHub linking)

## 1. Supabase project

- Create a project at [supabase.com](https://supabase.com) if you haven’t.
- Ensure **Authentication → Providers → Google** is enabled and your Google OAuth client ID/secret are set (use the same redirect URL Supabase shows).
- Create the `public.users` table (e.g. with a trigger that syncs from `auth.users` on sign-up).

## 2. Run the migration

In the [Supabase SQL Editor](https://supabase.com/dashboard/project/_/sql), run:

- **File:** `migrations/20260217000000_link_users_repos_github_tokens.sql`

This adds `owner_user_id` to `repositories`, `user_id` to `github_tokens`, and the `set_current_timestamp()` trigger function.

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
