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
