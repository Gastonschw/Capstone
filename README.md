# ERD Analysis Tool

A web application where teachers can upload an ERD (Entity-Relationship Diagram) image along with user stories text, and an AI agent analyzes whether the ERD properly supports the user stories.

## Features

- Upload ERD images (PNG, JPG, GIF, WebP)
- Enter user stories in text format
- AI-powered ERD extraction using Claude Vision
- Automated comparison of ERD against user stories
- Detailed mismatch report including:
  - Missing entities
  - Missing relationships
  - Cardinality issues
  - Orphaned entities
  - Missing attributes
- Coverage score and recommendations

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

4. Create a `.env` file with your Anthropic API key:
   ```
   ANTHROPIC_API_KEY=your_api_key_here
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

1. Open the application in your browser
2. Upload an ERD diagram image
3. Enter your user stories in the text area
4. Click "Analyze ERD"
5. Wait for the AI analysis to complete
6. Review the detailed report

## API Endpoints

- `POST /api/analyze` - Submit ERD image and user stories for analysis
- `GET /api/analysis/{id}` - Get analysis status and results
- `GET /api/analyses` - List all analyses (history)
- `GET /api/health` - Health check endpoint

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, SQLite, Anthropic Claude API
- **Frontend**: React, Vite, Axios
