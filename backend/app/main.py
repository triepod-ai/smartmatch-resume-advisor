"""Main FastAPI application for Resume Analyzer."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time

from app.config import settings
from app.models import AnalysisRequest, AnalysisResponse, ErrorResponse
from app.chains.analyzer import ResumeAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="SmartMatch Resume Advisor API",
    description="AI-powered resume analysis and optimization",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize analyzer
analyzer = ResumeAnalyzer()


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting Resume Analyzer API...")
    logger.info(f"Using model: {settings.model_name}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "model": settings.model_name}


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_resume(request: AnalysisRequest):
    """Analyze resume against job description."""
    try:
        start_time = time.time()
        logger.info("Starting resume analysis...")
        
        # Perform analysis
        result = await analyzer.analyze(
            resume_text=request.resume_text,
            job_description=request.job_description
        )
        
        processing_time = time.time() - start_time
        logger.info(f"Analysis completed in {processing_time:.2f} seconds")
        
        return result
        
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc) if settings.api_host == "0.0.0.0" else None,
            status_code=500
        ).dict()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
