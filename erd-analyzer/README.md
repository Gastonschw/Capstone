# ERD Analysis Tool

A web application where teachers can upload project repositories (via folder upload or GitHub integration), and an AI agent automatically discovers ERD diagrams and user stories, then analyzes whether the ERD properly supports the user stories.

## Features

### Repository Support
- **Folder Upload**: Upload a ZIP file containing your project
- **GitHub Integration**: Connect your GitHub account and import repositories directly
- **Automatic File Discovery**: AI-powered detection of ERD images and user story files

### Agentic Workflow
- **File Discovery Agent**: Scans repositories to identify ERD diagrams and user story files
- **ERD to UML Agent**: Converts visual ERD diagrams to structured UML class diagram format
- **Analysis Agent**: Compares UML structure against user stories for comprehensive coverage analysis

### Analysis Features
- AI-powered ERD extraction using Claude Vision
- Automated comparison of ERD against user stories
- Detailed mismatch report including:
  - Missing entities
  - Missing relationships
  - Cardinality issues
  - Orphaned entities
  - Missing attributes
  - Data integrity concerns
  - User story coverage breakdown
- Coverage score and actionable recommendations

### Legacy Support
- Single file upload still supported for quick analysis

## Setup

### Backend

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file based on `.env.example`:
   ```
   ANTHROPIC_API_KEY=your_api_key_here
   
   # Optional: GitHub OAuth for repository import
   GITHUB_CLIENT_ID=your_github_client_id
   GITHUB_CLIENT_SECRET=your_github_client_secret
   GITHUB_REDIRECT_URI=http://localhost:8000/api/github/callback
   GITHUB_TOKEN_ENCRYPTION_KEY=your_encryption_key
   ```

   To set up GitHub OAuth:
   1. Go to https://github.com/settings/developers
   2. Create a new OAuth App
   3. Set the callback URL to `http://localhost:8000/api/github/callback`
   4. Copy the Client ID and Client Secret to your `.env` file
   5. Generate an encryption key:
      ```bash
      python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
      ```

5. Start the backend server:
   ```bash
   uvicorn main:app --reload
   ```

   The API will be available at http://localhost:8000

### Frontend

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

   The app will be available at http://localhost:5173

## Usage

### Option 1: Folder Upload
1. Open the application in your browser
2. Click "Upload Folder" tab
3. Drag and drop a ZIP file containing your project
4. Wait for file discovery to complete
5. Review discovered ERD images and user story files
6. Select/deselect files as needed
7. Click "Analyze" to start the analysis
8. Review the detailed report

### Option 2: GitHub Import
1. Click "GitHub" tab
2. Click "Connect GitHub Account" and authorize the app
3. Search and select a repository
4. Click "Import Repository"
5. Review discovered files and start analysis

### Option 3: Single File (Legacy)
1. Click "Single File" tab
2. Upload an ERD diagram image
3. Enter your user stories in the text area
4. Click "Analyze ERD"

## API Endpoints

### Legacy Analysis
- `POST /api/analyze` - Submit ERD image and user stories for analysis
- `GET /api/analysis/{id}` - Get analysis status and results
- `GET /api/analyses` - List all analyses (history)

### GitHub Integration
- `GET /api/github/auth` - Initiate GitHub OAuth
- `GET /api/github/callback` - OAuth callback
- `GET /api/github/status` - Check authentication status
- `GET /api/github/repos` - List user repositories
- `POST /api/github/import` - Import a GitHub repository
- `POST /api/github/logout` - Disconnect GitHub

### Repository Management
- `POST /api/upload-folder` - Upload ZIP file for analysis
- `GET /api/repositories` - List all repositories
- `GET /api/repository/{id}` - Get repository details
- `GET /api/repository/{id}/files` - List discovered files
- `PUT /api/repository/{id}/files/selection` - Update file selection
- `POST /api/repository/{id}/rediscover` - Re-run file discovery
- `DELETE /api/repository/{id}` - Delete repository

### Repository Analysis
- `POST /api/repository/{id}/analyze` - Start analysis on repository
- `GET /api/repository/{id}/analyses` - List repository analyses

### Utility
- `GET /api/health` - Health check endpoint

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, SQLite, Anthropic Claude API, PyGithub
- **Frontend**: React, Vite, Axios

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│  Folder Upload  │     │  GitHub Import  │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
              ┌──────▼──────┐
              │  Repository │
              │   Storage   │
              └──────┬──────┘
                     │
         ┌───────────▼───────────┐
         │   Agent Orchestrator  │
         └───────────┬───────────┘
                     │
    ┌────────────────┼────────────────┐
    │                │                │
┌───▼───┐      ┌─────▼─────┐    ┌─────▼─────┐
│ File  │      │  ERD to   │    │ Analysis  │
│ Disc. │ ───► │    UML    │ ──►│   Agent   │
│ Agent │      │   Agent   │    │           │
└───────┘      └───────────┘    └─────┬─────┘
                                      │
                              ┌───────▼───────┐
                              │    Report     │
                              └───────────────┘
```
