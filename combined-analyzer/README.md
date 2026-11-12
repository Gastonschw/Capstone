# Combined Analyzer

A unified platform combining ERD Analysis and Integrity Analysis for comprehensive software project evaluation.

## Features

### ERD Analysis
- Analyzes ERD (Entity-Relationship Diagram) images against user stories
- Extracts UML structure from diagram images
- Identifies missing entities, relationships, and attributes
- Provides coverage scores and recommendations

### Integrity Analysis
- Evaluates 6 security characteristics:
  - **Confidentiality**: Access control and data protection
  - **Data Integrity**: Input validation and data corruption prevention
  - **Authenticity**: Authentication mechanisms
  - **Non-Repudiation**: Audit logging and traceability
  - **Accountability**: User action tracking
  - **Resistance**: Protection against common attacks (SQL injection, XSS, etc.)
- Provides overall security score and risk assessment

## Project Structure

```
combined-analyzer/
├── backend/
│   ├── main.py                    # FastAPI app with routers
│   ├── database.py                # Async SQLAlchemy setup
│   ├── config.py                  # Environment configuration
│   ├── models/                    # Database models
│   ├── schemas/                   # Pydantic schemas
│   ├── services/                  # Business logic
│   ├── routers/                   # API routes
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js
│   │   ├── main.jsx
│   │   └── components/
│   │       ├── common/
│   │       ├── upload/
│   │       ├── repository/
│   │       ├── erd/
│   │       └── integrity/
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- Anthropic API key

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ANTHROPIC_API_KEY=your_api_key
export GITHUB_CLIENT_ID=your_github_client_id      # Optional: for GitHub OAuth
export GITHUB_CLIENT_SECRET=your_github_secret     # Optional: for GitHub OAuth

# Run the server
uvicorn main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

The frontend will be available at http://localhost:5173

### Restored semester deployment

This branch retains the April 28 application behavior and Render's free backend plan. The public `/privacy.html` page is retained for the Google OAuth production configuration.

- Backend `backend/.env`: use the current Supabase session-pooler `DATABASE_URL`, keep `GITHUB_TOKEN_ENCRYPTION_KEY` stable, and set `FRONTEND_URL=http://localhost:5173` for local development. Preserve the existing GitHub and TAMU credentials.
- Frontend `frontend/.env`: set `VITE_API_URL=http://localhost:8000/api`, plus the same project's `VITE_SUPABASE_URL` and public `VITE_SUPABASE_ANON_KEY`. Both `.env` files are ignored by Git.
- In Render, use the deployed backend `/api` URL and frontend origin instead of localhost. Rebuild the frontend after changing its environment.
- Supabase Auth must allow `http://localhost:5173/analyzer` and the deployed frontend's `/analyzer` redirect. Keep Google OAuth in production for student access. New accounts start as general users; an administrator must assign the teacher role in `public.users`.
- The current Supabase database already has the application schema and identity triggers. This older backend creates missing ORM tables but does not apply SQL migrations automatically. Do not drop the migrated database or relax its existing RLS policies to restore this version.

Known semester-version limitations remain: backend identity relies on caller-supplied `X-User-Id`, and free Render storage is ephemeral. Uploaded source files can disappear on restarts/deploys even though database records remain. This restoration does not claim to fix those security or persistence issues.

Attached project notebooks are discovered from repository ZIPs and GitHub imports. Jupyter (`.ipynb`) code/Markdown cells are available to code-based analyses; cell outputs are excluded. Word (`.docx`) and PDF (`.pdf`) notebooks are extracted as requirements documentation and made available to ERD and quality-characteristic analyses.

## API Endpoints

### Shared
- `GET /api/repositories` - List repositories
- `GET /api/repository/{id}` - Get repository with files
- `DELETE /api/repository/{id}` - Delete repository
- `PUT /api/repository/{id}/files/selection` - Update file selection
- `POST /api/repository/{id}/rediscover` - Re-run discovery
- `POST /api/upload-folder` - Upload ZIP file

### GitHub OAuth
- `GET /api/github/auth` - Initiate OAuth
- `GET /api/github/callback` - OAuth callback
- `GET /api/github/status` - Check auth status
- `GET /api/github/repos` - List repos
- `POST /api/github/import` - Import repo
- `POST /api/github/logout` - Logout

### ERD Analysis
- `POST /api/erd/repository/{id}/analyze` - Start analysis
- `GET /api/erd/repository/{id}/analyses` - List analyses
- `GET /api/erd/analysis/{id}` - Get analysis

### Integrity Analysis
- `POST /api/integrity/repository/{id}/analyze` - Start analysis
- `GET /api/integrity/repository/{id}/analyses` - List analyses
- `GET /api/integrity/analysis/{id}` - Get analysis

## Usage

1. **Add a Repository**: Upload a ZIP file or connect GitHub to import a repository
2. **Review Discovered Files**: The system automatically scans and categorizes files
3. **Select Files**: Choose which files to include in each analysis type
4. **Run Analysis**: Select ERD analysis, Integrity analysis, or both
5. **View Reports**: Review detailed findings and recommendations

## Technology Stack

- **Backend**: FastAPI, SQLAlchemy (async), Anthropic Claude API
- **Frontend**: React 18, Vite, Axios
- **Database**: SQLite (async via aiosqlite)
