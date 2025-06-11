# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload  # Start development server on port 8000
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev    # Start development server on port 3000
npm run build  # Build for production
npm run lint   # Run ESLint
```

### Testing
```bash
cd backend
pytest  # Run backend tests
black .  # Format code
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