# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Quick Start (Recommended)
```bash
# From project root - easy commands using root package.json
npm run dev     # Start both backend and frontend
npm run build   # Build frontend for production
npm run lint    # Run ESLint on frontend
npm run setup   # Run initial project setup
```

### Individual Service Commands
```bash
# Backend specific
npm run dev:backend      # Start backend only (port 8000)
npm run install:backend  # Install Python dependencies
npm run test:backend     # Run backend tests

# Frontend specific  
npm run dev:frontend     # Start frontend only (port 3000)
npm run install:frontend # Install Node.js dependencies
npm run build:frontend   # Build frontend
npm run lint:frontend    # Lint frontend
```

### Manual Development (Alternative)
```bash
# Backend
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
uvicorn app.main:app --reload  # Start development server on port 8000

# Frontend
cd frontend
npm run dev    # Start development server on port 3000
```

### Environment Setup
```bash
# Automated setup (recommended)
npm run setup

# Manual setup
cp backend/.env.example backend/.env
# Edit .env to add OPENAI_API_KEY and other settings
```

## Architecture Overview

### Backend Structure
- **FastAPI app** (`app/main.py`): Main API server with CORS middleware and global exception handling
- **LangChain analyzer** (`app/chains/analyzer.py`): Core resume analysis using OpenAI GPT models, FAISS vector store, and structured LLM chains
- **Configuration** (`app/config.py`): Centralized settings using Pydantic with environment variable support
- **Prompt templates** (`app/chains/prompts.py`): Structured prompts for keyword extraction, match analysis, and bullet improvement

### Analysis Pipeline
1. **Keyword extraction**: Parallel extraction from resume and job description using LLM chains
2. **Vector similarity**: FAISS vector store with OpenAI embeddings for semantic matching
3. **Match analysis**: Structured JSON response with percentage, matched/missing keywords, strengths
4. **Bullet improvement**: AI-generated suggestions for resume bullet points

### Key Dependencies
- **LangChain**: Document processing, LLM chains, embeddings, vector stores
- **FastAPI**: Async web framework with automatic API documentation
- **OpenAI**: GPT models and embeddings (configurable via `settings.model_name`)
- **FAISS**: Vector similarity search for semantic keyword matching

### Environment Configuration
Copy `backend/.env.example` to `backend/.env` and configure:
- `OPENAI_API_KEY`: OpenAI API key for GPT and embeddings
- `MODEL_NAME`: OpenAI model (default: gpt-3.5-turbo)
- `EMBEDDING_MODEL`: OpenAI embedding model (default: text-embedding-ada-002)
- `FRONTEND_URL`: Frontend URL for CORS (default: http://localhost:3000)
- `LANGCHAIN_TRACING_V2`: Enable LangSmith tracing (optional)

### Frontend Architecture
- **Next.js 15** with TypeScript and App Router using Turbopack
- **Tailwind CSS v4** with shadcn/ui components
- **React Hook Form** with Zod validation
- **Axios** for API communication with the FastAPI backend
- Frontend expects backend on port 8000, frontend runs on port 3000

## API Reference

Main endpoint: `POST /analyze` - accepts `resume_text` and `job_description`, returns match analysis with percentage, keywords, suggestions, and feedback.

## Development Notes

- Analysis chains use async/await for parallel keyword extraction and improved performance
- Text processing includes chunking (1000 chars, 200 overlap) for large documents
- Built-in rate limiting and error handling for production deployment
- Response models use Pydantic for type safety and automatic API documentation
- Vector embeddings enable semantic similarity beyond simple keyword matching
- FastAPI automatically generates interactive docs at `/docs` endpoint

### File Upload Support
- Frontend supports drag-and-drop .txt file upload for resume input
- File validation enforces text format and minimum character requirements
- Sample data available via button for quick testing without file upload

### Component Architecture
- Custom React hooks (`useAnalyzeResume`) manage API state and error handling
- Modular components in `src/components/forms/` and `src/components/results/`
- Copy-to-clipboard functionality for improved bullet points
- Color-coded match percentage (red <60%, yellow 60-80%, green >80%)

### Development Workflow
- Backend runs on port 8000, frontend on port 3000
- Full TypeScript coverage with interfaces matching backend Pydantic models
- Environment-based API URL configuration for different deployment targets