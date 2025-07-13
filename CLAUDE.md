# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**SmartMatch Resume Analyzer** is a production-ready NLP application that demonstrates modern AI techniques for career optimization. This is a **personal-use demo version** of a larger SaaS application, designed for ReadyTensor certification and educational purposes.

### Key Characteristics
- **Simple & Focused**: Personal-use tool, not a complex multi-tenant SaaS
- **Educational**: Demonstrates NLP best practices and modern development patterns
- **Production-Quality**: Real AI analysis with robust error handling and fallback systems
- **Certification-Ready**: Meets ReadyTensor Essential criteria (85%+ compliance)

## Development Commands

### Quick Start (Recommended)
```bash
# From project root - streamlined commands using root package.json
npm run setup   # Run initial project setup (ALWAYS run this first)
npm run dev     # Start both backend and frontend
npm run build   # Build frontend for production
npm run start   # Start production frontend

# Quality Assurance
npm run test    # Run all tests (backend + frontend)
npm run lint    # Run linting (both Python and JavaScript)
npm run format  # Run code formatting (Black + Prettier)
npm run validate # Validate environment configuration

# Log Management
npm run logs        # Monitor application logs in real-time
npm run logs:clear  # Clear application log files
```

### Testing Commands
```bash
npm run test              # Run all tests
npm run test:backend      # Run backend Python tests only
npm run test:frontend     # Run frontend React tests only  
npm run test:coverage     # Run tests with coverage reports
```

### Manual Development (Alternative)
```bash
# Backend (Python 3.11+ with virtual environment)
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload  # Start development server on port 8000

# Backend Testing
cd backend && source .venv/bin/activate
pytest                     # Run all backend tests
pytest -v                 # Verbose output
pytest --cov=app         # With coverage
flake8 .                  # Run linting
black .                   # Run code formatting

# Frontend (Next.js 15 + TypeScript)
cd frontend
npm run dev               # Start development server on port 3000
npm run test             # Run component tests
npm run lint             # Run ESLint
npx prettier --write .   # Format code
```

### Environment Setup
```bash
# Automated setup (recommended) - handles everything
npm run setup

# Validate setup worked correctly
npm run validate

# Manual setup (if needed)
cd backend
cp .env.example .env
# Edit .env to add OPENAI_API_KEY (required)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd ../frontend
npm install
```

### Environment Configuration
The `.env` file in `backend/` requires:
- **OPENAI_API_KEY** (required): Get from https://platform.openai.com/api-keys
- **MODEL_NAME** (optional): Defaults to gpt-3.5-turbo
- **FRONTEND_URL** (optional): Defaults to http://localhost:3000
- See `backend/.env.example` for full configuration options

## Architecture Overview

### Backend Structure
- **FastAPI app** (`app/main.py`): Main API server with CORS middleware, request logging, and global exception handling
- **LangChain analyzer** (`app/chains/analyzer.py`): Core resume analysis using OpenAI GPT models with intelligent response normalization
- **Logging system** (`app/logging_config.py`): Structured logging with file rotation, request tracking, and performance monitoring
- **Configuration** (`app/config.py`): Centralized settings using Pydantic with environment variable support
- **Prompt templates** (`app/chains/prompts.py`): Structured prompts for keyword extraction, match analysis, and bullet improvement

### Analysis Pipeline
1. **Input Validation**: Comprehensive validation of resume and job description text
2. **Keyword extraction**: Parallel extraction from resume and job description using LLM chains
3. **AI-powered matching**: GPT-3.5-turbo semantic analysis with intelligent keyword comparison
4. **Response normalization**: Automatic conversion of LLM string responses to structured lists
5. **Match analysis**: Structured JSON response with percentage, matched/missing keywords, strengths
6. **Bullet improvement**: AI-generated suggestions for resume bullet points
7. **Fallback system**: Graceful degradation to rule-based keyword matching when LLM analysis fails
8. **Error handling**: Comprehensive error recovery and user-friendly error messages

### Key Dependencies
- **LangChain**: Document processing, LLM chains, and text splitting
- **FastAPI**: Async web framework with automatic API documentation
- **OpenAI**: GPT models for intelligent analysis (configurable via `settings.model_name`)
- **Pydantic**: Type safety and automatic validation with response normalization
- **uv**: Fast Python package installer and virtual environment manager (recommended for WSL)

### Environment Configuration
Copy `backend/.env.example` to `backend/.env` and configure:
- `OPENAI_API_KEY`: OpenAI API key for GPT analysis (required)
- `MODEL_NAME`: OpenAI model (default: gpt-3.5-turbo)
- `FRONTEND_URL`: Frontend URL for CORS (default: http://localhost:3000)
- `DEBUG`: Enable debug logging (default: false)
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

### Core Features
- **Sub-3 Second Analysis**: Typically 0.8-2.6 seconds for complete resume analysis
- **Production-Ready Error Handling**: Automatic fallback when OpenAI API unavailable
- **Type Safety**: Full Pydantic validation for all API requests/responses
- **Async Processing**: Parallel keyword extraction for optimal performance
- **Response Normalization**: Handles LLM output variations automatically

### Testing Infrastructure
- **Backend**: Comprehensive pytest test suite with fixtures and mocks
- **Frontend**: Vitest + Testing Library for component and integration testing
- **Quality Assurance**: ESLint, Prettier, Black, Flake8 for code quality
- **Environment Validation**: Automated checks for dependencies and configuration

### Important File Locations
- **Main API**: `backend/app/main.py`
- **Analysis Logic**: `backend/app/chains/analyzer.py`
- **Frontend Components**: `frontend/src/components/forms/AnalysisForm.tsx`
- **Test Files**: `backend/tests/` and `frontend/src/__tests__/`
- **Configuration**: `backend/.env` (copy from `.env.example`)

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

## Logging & Monitoring

### Application Logging Structure
```
backend/app-logs/
├── app.log       # General application logs (INFO level)
├── access.log    # HTTP request/response logs
└── error.log     # Error and exception logs
```

### Log Management Commands
```bash
# Monitor logs in real-time
npm run logs         # Application logs
tail -f backend/app-logs/access.log  # HTTP requests
tail -f backend/app-logs/error.log   # Errors only

# Clear logs
npm run logs:clear   # Clear all application logs

# API endpoints for monitoring
curl http://localhost:8000/logs/status  # Log status endpoint
curl http://localhost:8000/health       # Health check
```

### Log Features
- **Automatic rotation**: 10MB files, 5 backups per log type
- **Structured logging**: Timestamp, logger name, level, message
- **Request tracking**: HTTP method, path, status, timing, client IP
- **Analysis logging**: Resume/job description length, processing time, success/failure
- **Error context**: Full stack traces for debugging
- **Separation**: Application logs separate from MCP infrastructure logs

### Monitoring Endpoints
- `GET /health` - Basic health check with model info
- `GET /logs/status` - Log file status and sizes

## Production Status & Performance

### ✅ **Confirmed Working Features (Live Tested)**
- **Real AI Analysis**: GPT-3.5-turbo providing intelligent resume analysis
- **Performance**: Sub-3 second response times (0.8s - 2.6s measured)
- **Error Handling**: Automatic LLM response normalization and graceful fallbacks
- **Testing**: Comprehensive test suite for backend API and frontend components
- **Code Quality**: Linting, formatting, and validation tools configured
- **Environment Validation**: Automated setup verification and troubleshooting

### **Live Performance Metrics**
- **Analysis Speed**: 0.8s - 2.6s per request (varies by content size)
- **Success Rate**: 100% with automatic error recovery and fallback systems
- **Content Processing**: Handles 264-2131+ character resumes effectively
- **Test Coverage**: Backend API endpoints and frontend components fully tested
- **Quality Standards**: All code passes linting and formatting checks

### **Known Working Configuration**
- **Backend**: Python 3.11+ with virtual environment (.venv)
- **Dependencies**: LangChain + FastAPI + OpenAI (tested and stable versions)
- **Frontend**: Next.js 15 + TypeScript + Tailwind CSS v4 + Vitest
- **Testing**: pytest (backend) + Vitest + Testing Library (frontend)
- **Code Quality**: Black, Flake8 (Python) + ESLint, Prettier (JS/TS)
- **Environment**: Cross-platform (WSL2, macOS, Linux)

## Troubleshooting

### Common Issues When Using Claude Code

1. **"Tests are failing"**
   ```bash
   npm run validate  # Check environment first
   npm run setup     # Reinstall dependencies
   ```

2. **"Missing OpenAI API key"**
   - Copy `backend/.env.example` to `backend/.env`
   - Add your OpenAI API key to the `.env` file
   - Run `npm run validate` to verify

3. **"Import errors or module not found"**
   ```bash
   npm run setup  # Reinstalls both backend and frontend dependencies
   ```

4. **"Virtual environment issues"**
   - The project uses `.venv` directory (not `venv`)
   - Created with `python3 -m venv .venv` (not uv)
   - Activated with `source .venv/bin/activate`

5. **"Frontend won't start"**
   ```bash
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   npm run dev
   ```

### Health Checks
```bash
npm run validate           # Full environment validation
curl localhost:8000/health # Backend health check (if running)
npm run test              # Run all tests to verify functionality
```