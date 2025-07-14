"""Main resume analyzer using LangChain.

Copyright (c) 2024 SmartMatch Resume Analyzer
Licensed under the MIT License. See LICENSE file for details.
"""

import json
import asyncio
import time
from typing import Dict, List, Any
import logging

from langchain_openai import ChatOpenAI
# Updated imports for modern LangChain
from langchain.text_splitter import RecursiveCharacterTextSplitter
# OpenAI embeddings and FAISS for semantic analysis
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
from app.chains.utils import (
    normalize_match_result,
    extract_from_natural_language,
    apply_semantic_boost,
    simple_keyword_match,
    extract_bullet_points,
    generate_feedback
)
from app.exceptions import (
    AnalysisError,
    ValidationError,
    APIError,
    ModelError,
    DataProcessingError,
    TimeoutError,
    RateLimitError
)

logger = logging.getLogger(__name__)


class ResumeAnalyzer:
    """
    Main class for analyzing resumes against job descriptions.
    
    Advanced version using hybrid approach: LLM-based keyword extraction 
    combined with FAISS vector similarity for semantic analysis. Includes 
    fallback to simple keyword matching when advanced analysis fails.
    """
    
    def __init__(self):
        """Initialize the analyzer with LangChain components."""
        self.llm = ChatOpenAI(
            model=settings.model_name,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            openai_api_key=settings.openai_api_key
        )
        
        # Initialize embeddings for semantic analysis
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=settings.openai_api_key
        )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap
        )
        
        # Initialize modern LangChain chains using pipe syntax
        self.keyword_chain = KEYWORD_EXTRACTION_PROMPT | self.llm
        self.match_chain = MATCH_ANALYSIS_PROMPT | self.llm  
        self.improvement_chain = BULLET_IMPROVEMENT_PROMPT | self.llm

    async def analyze(self, resume_text: str, job_description: str) -> AnalysisResponse:
        """Perform complete resume analysis."""
        start_time = time.time()
        
        # Input validation with custom exceptions
        if not resume_text or not resume_text.strip():
            raise ValidationError(
                "Resume text cannot be empty",
                field_name="resume_text",
                validation_type="required"
            )
        
        if not job_description or not job_description.strip():
            raise ValidationError(
                "Job description cannot be empty",
                field_name="job_description", 
                validation_type="required"
            )
        
        if len(resume_text.strip()) < 50:
            raise ValidationError(
                "Resume text must be at least 50 characters long",
                field_name="resume_text",
                validation_type="min_length",
                min_length=50,
                actual_length=len(resume_text.strip())
            )
        
        try:
            # Extract keywords from both texts and generate embeddings in parallel
            resume_keywords_task = self._extract_keywords(resume_text, "resume")
            jd_keywords_task = self._extract_keywords(job_description, "job description")
            semantic_analysis_task = self._perform_semantic_analysis(resume_text, job_description)
            
            resume_keywords, jd_keywords, semantic_score = await asyncio.gather(
                resume_keywords_task,
                jd_keywords_task,
                semantic_analysis_task
            )
            
            # Perform hybrid match analysis (keywords + semantic)
            match_result = await self._analyze_match(
                resume_keywords,
                jd_keywords,
                resume_text,
                job_description,
                semantic_score
            )
            
            # Extract bullet points and generate improvements
            bullet_points = extract_bullet_points(resume_text)
            suggestions = []
            
            if bullet_points and match_result.get("missing_keywords"):
                improvement_result = await self._improve_bullets(
                    bullet_points[:5],  # Limit to top 5 bullets
                    job_description,
                    match_result["missing_keywords"]
                )
                suggestions = improvement_result
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Build response
            return AnalysisResponse(
                match_percentage=match_result.get("match_percentage", 0),
                matched_keywords=match_result.get("matched_keywords", []),
                missing_keywords=match_result.get("missing_keywords", []),
                suggestions=suggestions,
                strengths=match_result.get("strengths", []),
                areas_for_improvement=match_result.get("improvements", []),
                overall_feedback=generate_feedback(match_result),
                processing_time=processing_time
            )
            
        except ValidationError:
            # Re-raise validation errors as they are already properly typed
            raise
        except APIError:
            # Re-raise API errors as they are already properly typed
            raise
        except Exception as e:
            logger.error(f"Analysis error: {str(e)}", exc_info=True)
            raise AnalysisError(
                f"Failed to complete resume analysis: {str(e)}", 
                analysis_type="full_analysis",
                processing_stage="main_pipeline"
            )

    async def _extract_keywords(self, text: str, context: str) -> List[str]:
        """Extract keywords from text."""
        try:
            result = await self.keyword_chain.ainvoke({"text": text, "context": context})
            result = result.content  # Extract content from AIMessage
            keywords = [k.strip() for k in result.split(",") if k.strip()]
            return keywords[:30]  # Limit to 30 keywords
        except Exception as e:
            logger.error(f"Keyword extraction error: {str(e)}")
            # For keyword extraction, we can continue with empty list as fallback
            raise DataProcessingError(
                f"Failed to extract keywords from {context}: {str(e)}",
                data_type=context,
                processing_step="keyword_extraction"
            )
    
    async def _perform_semantic_analysis(self, resume_text: str, job_description: str) -> float:
        """Perform semantic similarity analysis using FAISS vector search."""
        try:
            # Split documents into chunks for better vector representation
            resume_chunks = self.text_splitter.split_text(resume_text)
            jd_chunks = self.text_splitter.split_text(job_description)
            
            # Create documents for vector store
            resume_docs = [Document(page_content=chunk, metadata={"type": "resume"}) for chunk in resume_chunks]
            
            # Create FAISS vector store from resume documents
            if resume_docs:
                vector_store = await asyncio.get_event_loop().run_in_executor(
                    None, FAISS.from_documents, resume_docs, self.embeddings
                )
                
                # Calculate semantic similarity for each job description chunk
                similarities = []
                for jd_chunk in jd_chunks:
                    similar_docs = await asyncio.get_event_loop().run_in_executor(
                        None, vector_store.similarity_search_with_score, jd_chunk, 3
                    )
                    if similar_docs:
                        # Get the best similarity score for this chunk
                        best_score = min([score for _, score in similar_docs])  # Lower is better in FAISS
                        # Convert to 0-1 scale (approximate)
                        normalized_score = max(0, 1 - (best_score / 2))
                        similarities.append(normalized_score)
                
                if similarities:
                    # Return average semantic similarity
                    semantic_score = sum(similarities) / len(similarities)
                    logger.info(f"Semantic similarity score: {semantic_score:.3f}")
                    return semantic_score
                
            return 0.0
            
        except Exception as e:
            logger.error(f"Semantic analysis error: {str(e)}")
            return 0.0  # Fallback to no semantic boost
    
    async def _analyze_match(
        self,
        resume_keywords: List[str],
        job_keywords: List[str],
        resume_text: str,
        job_description: str,
        semantic_score: float = 0.0
    ) -> Dict[str, Any]:
        """Analyze resume-job match using LLM with advanced three-tier parsing."""
        try:
            result = await self.match_chain.ainvoke({
                "resume_keywords": ", ".join(resume_keywords),
                "job_keywords": ", ".join(job_keywords),
                "resume_text": resume_text[:3000],  # Limit text length
                "job_description": job_description[:3000]
            })
            result = result.content  # Extract content from AIMessage
            
            # Three-tier response normalization system
            parsed_result = await self._parse_llm_response(result, resume_keywords, job_keywords, semantic_score)
            
            return parsed_result
            
        except Exception as e:
            logger.error(f"LLM match analysis failed: {str(e)}, using fallback matching")
            return simple_keyword_match(resume_text, job_description, resume_keywords, job_keywords)
    
    async def _parse_llm_response(
        self, 
        raw_response: str, 
        resume_keywords: List[str], 
        job_keywords: List[str],
        semantic_score: float
    ) -> Dict[str, Any]:
        """Three-tier response parsing system for production reliability."""
        
        # Tier 1: Parse structured JSON response
        try:
            parsed_result = json.loads(raw_response)
            logger.info("Tier 1: Successfully parsed structured JSON response")
            normalized_result = normalize_match_result(parsed_result)
            # Apply semantic boost to LLM result if available
            if semantic_score > 0:
                normalized_result = apply_semantic_boost(normalized_result, semantic_score)
            return normalized_result
            
        except json.JSONDecodeError:
            logger.warning("Tier 1 failed: JSON parsing error, trying text extraction")
            
        # Tier 2: Extract from natural language using regex patterns
        try:
            extracted_result = extract_from_natural_language(raw_response, resume_keywords, job_keywords)
            logger.info("Tier 2: Successfully extracted from natural language")
            if semantic_score > 0:
                extracted_result = apply_semantic_boost(extracted_result, semantic_score)
            return extracted_result
            
        except Exception as e:
            logger.warning(f"Tier 2 failed: Text extraction error: {str(e)}")
            
        # Tier 3: Rule-based fallback with semantic enhancement
        logger.info("Tier 3: Using rule-based fallback matching")
        result = simple_keyword_match("", "", resume_keywords, job_keywords)
        return apply_semantic_boost(result, semantic_score)
    

    async def _improve_bullets(
        self,
        bullet_points: List[str],
        job_description: str,
        missing_keywords: List[str]
    ) -> List[BulletSuggestion]:
        """Generate improved bullet points."""
        try:
            result = await self.improvement_chain.ainvoke({
                "bullet_points": "\n".join(f"- {bp}" for bp in bullet_points),
                "job_description": job_description[:2000],
                "missing_keywords": ", ".join(missing_keywords[:10])
            })
            result = result.content  # Extract content from AIMessage
            
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
    
