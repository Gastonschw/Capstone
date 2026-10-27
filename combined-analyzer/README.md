# Combined Analyzer

Authenticated repository analysis for ERD coverage, integrity, compliance, correctness, usability, and maintainability, with report chat and comparisons.

## Requirements

- Python 3.10 or later; deployment uses Python 3.11.
- Node.js 22.12 or later (the Render blueprint pins 22.22.0).
- A Supabase project with Google Auth enabled and a PostgreSQL connection available to the backend. SQLite and anonymous access are not supported.
- A TAMU API key and a model capable of the requested analysis; image ERDs require vision support.
- Persistent filesystem storage for imported repositories in production.

## Backend configuration

Set environment variables or create `backend/.env`. Do not commit credentials.

| Variable | Requirement |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection URI for a trusted owner/BYPASSRLS database role. Use a direct connection or Supabase's IPv4-compatible session pooler, not transaction pooling: the worker guard requires a persistent database session. An unavailable database fails startup; it never falls back to another database. |
| `SUPABASE_URL` | Supabase project URL; HTTPS required except localhost development. |
| `SUPABASE_ANON_KEY` | Project anon/publishable API key, used with the caller's bearer token to verify `/auth/v1/user`. This is not a service-role key. |
| `GITHUB_TOKEN_ENCRYPTION_KEY` | Persistent Fernet key. Required even before GitHub is connected. Keep it unchanged across restarts and back it up separately. |
| `FRONTEND_URL` | Exact frontend origin, e.g. `http://localhost:5173`. Used for CORS and OAuth redirects. |
| `REPOS_DIR` | Persistent repository directory. Defaults to an absolute resolution of `uploads/repos` relative to the backend working directory. Render sets `/var/data/repos`. |
| `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` | GitHub OAuth app credentials when GitHub import is enabled. |
| `GITHUB_REDIRECT_URI` | OAuth app callback, e.g. `https://your-api.example/api/github/callback`. Must match GitHub's registration. |
| `TAMU_API_KEY` | Optional server fallback. Users can supply their own key in the UI. |
| `TAMU_API_BASE`, `TAMU_MODELS_URL`, `TAMU_MODEL` | Optional provider endpoint/default-model overrides. |

Alternatively, a complete `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, and `DB_NAME` set can supply the database connection. `DATABASE_URL` takes precedence.

Generate an encryption key once:

```sh
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Losing or replacing this key makes existing encrypted GitHub credentials unusable; reconnect GitHub after an intentional rotation. Never generate a new key on every deployment.

## Startup and database migrations

```sh
cd combined-analyzer/backend
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```

Startup creates application tables and applies every checked-in Supabase migration transactionally, in filename order, before serving requests. Applied filenames are recorded in `public.application_schema_migrations`. A failed migration rolls back the schema changes and stops startup. See [Supabase setup](supabase/README.md) for identity bootstrap, permissions, upgrades, and administrator assignment.

Run **exactly one web worker/instance**. A PostgreSQL advisory session lock rejects a second active worker. Analysis jobs run in the web process; startup marks interrupted pending/processing jobs failed with a retry instruction. Jobs are not silently resumed or left polling forever.

## Frontend configuration

Create `frontend/.env` from `.env.example`:

```dotenv
VITE_API_URL=http://localhost:8000/api
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-project-anon-key
```

`VITE_API_URL` includes `/api`. If omitted, the Vite development proxy uses `/api` on port 8000. Missing Supabase configuration produces an explicit configuration error rather than an unusable anonymous analyzer.

```sh
cd combined-analyzer/frontend
npm ci
npm run dev
```

Allow the frontend origin and `/analyzer` redirect in Supabase Auth. Enable Google and configure its provider credentials in Supabase. Supabase JWTs are sent in `Authorization: Bearer ...`; `X-User-Id` is not authentication and is ignored.

## GitHub OAuth

1. The signed-in frontend posts to `/api/github/auth` using its Supabase bearer token.
2. The returned `authorization_url` is a short-lived, one-use API navigation ticket.
3. Top-level navigation exchanges that ticket for an independent state nonce and an HttpOnly, SameSite=Lax browser-binding cookie, then redirects to GitHub.
4. The callback verifies and consumes the state/cookie pair and creates a new owner-bound session. The frontend consumes the callback before routing and verifies its session with the backend before storing it.

The first-party navigation supports separate frontend/API sites without depending on third-party cookies. All token operations require the verified application user as well as the session. Reconnecting rotates existing sessions; signing out revokes the current GitHub session and clears browser-held GitHub/TAMU credentials. Cookies use Secure when the configured callback uses HTTPS.

## Repository and analysis behavior

- ZIP and GitHub imports are transactional: repository/discovery rows commit together; failures clean up extracted files and temporary archives.
- Archives are streamed and limited to 100 MiB compressed, 512 MiB expanded, 32 MiB per entry, and 10,000 entries. Traversal, Windows rooted/drive paths, links, and special files are rejected.
- Rediscovery builds replacement candidates before changing saved discoveries. Missing/unreadable sources or database failures retain prior selections. A failed optional AI classification falls back to file heuristics, not invented files.
- Repository lists use `limit` (1–100, default 50) and `offset`; the frontend loads all pages. Teacher inspection uses the same pagination.
- Each analysis saves its selected file paths/types at submission and validates their complete content before dispatch. Current code/text context capacity is **200,000 source bytes per run**; over-capacity selections fail explicitly instead of silently omitting files. Chat uses the saved selection, never later repository selection flags.
- ERD runs require schema content and user stories. All selected textual schemas are merged. PNG, JPEG, GIF, and WebP are supported image inputs; SVG/BMP must be converted before upload/selection and are not mislabeled as PNG.
- Invalid, incomplete, refused, or malformed model reports fail the run. They are never assigned synthetic scores. A provider/network error in chat is a structured SSE error, not assistant content.
- Comparisons require valid one-to-one match output and support up to 200 findings on each side. Larger inputs or invalid responses show an explicit error, not a false resolved/new report.
- Additional class administrators can manage their class and inspect enrolled students' repositories. Only the creator can promote/revoke administrators or delete the class; global administrators can create classes.

## Render deployment and upgrades

`render.yaml` uses a **paid Starter backend and a 10 GiB persistent disk** mounted at `/var/data`. Applying that blueprint incurs Render charges; editing it does not deploy anything. The frontend uses `npm ci` and a supported Node version.

Before deploying this cutover:

1. Back up PostgreSQL, the repository directory, and the encryption key. Preserve existing valid encryption keys.
2. Configure all required backend/frontend variables and OAuth redirect URLs. The database user must be able to create tables, apply migrations, and bypass RLS for backend operations.
3. Copy existing repository directories onto the persistent disk before replacing the old instance. Update existing `repositories.local_path` values to their copied absolute paths. Paths recorded on Windows must not be reused verbatim on Linux. Files already lost from an ephemeral instance cannot be reconstructed from metadata or previews; reimport them.
4. Start one backend worker. Startup applies identity, cascade, snapshot, OAuth-state, and RLS migrations. Ownerless legacy GitHub tokens are removed because they cannot be safely attributed; users must reconnect them. Ownerless legacy repositories are not reassigned automatically—resolve ownership administratively or remove/reimport them after reviewing the data.
5. Existing completed reports remain readable. Their original file selections cannot be reconstructed, so chat on legacy runs without snapshots requires a new analysis. Interrupted runs become failed/retryable.
6. Verify `/api/health`, Google sign-in, class enrollment, upload, one analysis, GitHub connection, and a restart preserving imported source files.

Direct account deletion through Supabase cascades relational records. Filesystem repository directories are not part of a PostgreSQL transaction; operational deletion of accounts must also remove their corresponding persisted directories after recording those paths.

## Verification commands

Run backend regressions with the required environment configured:

```sh
cd combined-analyzer/backend
python -m unittest discover -s tests -v
```

Production build and dependency checks:

```sh
cd combined-analyzer/frontend
npm run build
npm audit
```

Backend dependency audit (install `pip-audit` in a development environment):

```sh
python -m pip_audit -r combined-analyzer/backend/requirements.txt
```

## Security/correctness cutover — 2026-10-27

Replaced caller-supplied identity with verified bearer authentication; bound OAuth to owner/browser; restricted Supabase API grants; bounded and transactionalized imports; added cascading deletes, input snapshots, interrupted-job recovery, strict report validation, asynchronous chat, independent UI polling, comparison/error handling, complete repository pagination, and patched dependency versions. PostgreSQL/Supabase and persistent production storage are now explicit requirements.
