"""Main resume analyzer using LangChain."""

import json
import asyncio
from typing import Dict, List, Any
import logging

from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.schema import Document

from app.config import settings
from app.models import AnalysisResponse, BulletSuggestion
from app.chains.prompts import (
    KEYWORD_EXTRACTION_PROMPT,
    MATCH_ANALYSIS_PROMPT,
    BULLET_IMPROVEMENT_PROMPT
)

logger = logging.getLogger(__name__)


class ResumeAnalyzer:
    """Main class for analyzing resumes against job descriptions."""
    
    def __init__(self):
        """Initialize the analyzer with LangChain components."""
        self.llm = ChatOpenAI(
            model=settings.model_name,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            openai_api_key=settings.openai_api_key
        )
        
        self.embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            openai_api_key=settings.openai_api_key
        )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap
        )
        
        # Initialize chains
        self.keyword_chain = LLMChain(
            llm=self.llm,
            prompt=KEYWORD_EXTRACTION_PROMPT
        )
        
        self.match_chain = LLMChain(
            llm=self.llm,
            prompt=MATCH_ANALYSIS_PROMPT
        )
        
        self.improvement_chain = LLMChain(
            llm=self.llm,
            prompt=BULLET_IMPROVEMENT_PROMPT
        )

    async def analyze(self, resume_text: str, job_description: str) -> AnalysisResponse:
        """Perform complete resume analysis."""
        try:
            # Extract keywords from both texts
            resume_keywords_task = self._extract_keywords(resume_text, "resume")
            jd_keywords_task = self._extract_keywords(job_description, "job description")
            
            resume_keywords, jd_keywords = await asyncio.gather(
                resume_keywords_task,
                jd_keywords_task
            )
            
            # Perform match analysis
            match_result = await self._analyze_match(
                resume_keywords,
                jd_keywords,
                resume_text,
                job_description
            )
            
            # Extract bullet points and generate improvements
            bullet_points = self._extract_bullet_points(resume_text)
            suggestions = []
            
            if bullet_points and match_result.get("missing_keywords"):
                improvement_result = await self._improve_bullets(
                    bullet_points[:5],  # Limit to top 5 bullets
                    job_description,
                    match_result["missing_keywords"]
                )
                suggestions = improvement_result
            
            # Build response
            return AnalysisResponse(
                match_percentage=match_result.get("match_percentage", 0),
                matched_keywords=match_result.get("matched_keywords", []),
                missing_keywords=match_result.get("missing_keywords", []),
                suggestions=suggestions,
                strengths=match_result.get("strengths", []),
                areas_for_improvement=match_result.get("improvements", []),
                overall_feedback=self._generate_feedback(match_result)
            )
            
        except Exception as e:
            logger.error(f"Analysis error: {str(e)}", exc_info=True)
            raise

    async def _extract_keywords(self, text: str, context: str) -> List[str]:
        """Extract keywords from text."""
        try:
            result = await self.keyword_chain.arun(text=text, context=context)
            keywords = [k.strip() for k in result.split(",") if k.strip()]
            return keywords[:30]  # Limit to 30 keywords
        except Exception as e:
            logger.error(f"Keyword extraction error: {str(e)}")
            return []
    
    async def _analyze_match(
        self,
        resume_keywords: List[str],
        job_keywords: List[str],
        resume_text: str,
        job_description: str
    ) -> Dict[str, Any]:
        """Analyze resume-job match."""
        try:
            result = await self.match_chain.arun(
                resume_keywords=", ".join(resume_keywords),
                job_keywords=", ".join(job_keywords),
                resume_text=resume_text[:3000],  # Limit text length
                job_description=job_description[:3000]
            )
            
            # Parse JSON response
            return json.loads(result)
        except json.JSONDecodeError:
            # Fallback parsing if JSON fails
            return {
                "match_percentage": 50,
                "matched_keywords": list(set(resume_keywords) & set(job_keywords)),
                "missing_keywords": list(set(job_keywords) - set(resume_keywords)),
                "strengths": ["Unable to parse detailed analysis"],
                "improvements": ["Please try again"]
            }

    async def _improve_bullets(
        self,
        bullet_points: List[str],
        job_description: str,
        missing_keywords: List[str]
    ) -> List[BulletSuggestion]:
        """Generate improved bullet points."""
        try:
            result = await self.improvement_chain.arun(
                bullet_points="\n".join(f"- {bp}" for bp in bullet_points),
                job_description=job_description[:2000],
                missing_keywords=", ".join(missing_keywords[:10])
            )
            
            # Parse JSON response
            improvements = json.loads(result)
            return [
                BulletSuggestion(**item)
                for item in improvements
                if all(k in item for k in ["original", "improved", "reason"])
            ]
        except Exception as e:
            logger.error(f"Bullet improvement error: {str(e)}")
            return []
    
    def _extract_bullet_points(self, resume_text: str) -> List[str]:
        """Extract bullet points from resume."""
        lines = resume_text.split("\n")
        bullets = []
        
        for line in lines:
            line = line.strip()
            if any(line.startswith(marker) for marker in ["•", "-", "*", "·"]):
                cleaned = line.lstrip("•-*· ").strip()
                if len(cleaned) > 20:  # Minimum length for a bullet
                    bullets.append(cleaned)
        
        return bullets
    
    def _generate_feedback(self, match_result: Dict[str, Any]) -> str:
        """Generate overall feedback message."""
        percentage = match_result.get("match_percentage", 0)
        
        if percentage >= 80:
            level = "excellent"
        elif percentage >= 60:
            level = "good"
        elif percentage >= 40:
            level = "moderate"
        else:
            level = "low"
        
        return f"Your resume shows a {level} match ({percentage}%) with the job description. " \
               f"Focus on incorporating the missing keywords and highlighting relevant experience."
