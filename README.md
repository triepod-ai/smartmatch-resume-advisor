# SmartMatch Resume Advisor

An AI-powered resume analyzer that provides intelligent feedback on resume-job description alignment using LangChain and OpenAI.

## Quick Start

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd ai-resume-analyzer-with-langchain
   chmod +x scripts/setup.sh
   ./scripts/setup.sh
   ```

2. **Add your OpenAI API key:**
   ```bash
   # Edit backend/.env and add your key
   OPENAI_API_KEY=your_key_here
   ```

3. **Start development:**
   ```bash
   chmod +x scripts/dev-start.sh
   ./scripts/dev-start.sh
   ```

4. **Open in browser:** http://localhost:3000

## Documentation

- [📋 Development Commands](CLAUDE.md) - For Claude Code users
- [🏗️ Architecture Overview](docs/ARCHITECTURE.md)
- [🚀 Implementation Plan](docs/IMPLEMENTATION_PLAN.md)

## Tech Stack

- **Backend**: Python, FastAPI, LangChain, OpenAI
- **Frontend**: Next.js 15, TypeScript, Tailwind CSS v4
- **AI/ML**: OpenAI GPT models, FAISS Vector Store
- **Deployment**: Vercel (Frontend), Railway/Render (Backend)

## Features

- Smart match analysis with percentage scoring
- Keyword gap identification
- AI-powered improvement suggestions
- Fast processing (< 5 seconds)
- Mobile-responsive interface

---

**Built with ❤️ using LangChain and modern web technologies**