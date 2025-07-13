"""Main resume analyzer using LangChain."""

import json
import asyncio
import time
from typing import Dict, List, Any
import logging

from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
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
            bullet_points = self._extract_bullet_points(resume_text)
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
                overall_feedback=self._generate_feedback(match_result),
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
            result = await self.keyword_chain.arun(text=text, context=context)
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
            result = await self.match_chain.arun(
                resume_keywords=", ".join(resume_keywords),
                job_keywords=", ".join(job_keywords),
                resume_text=resume_text[:3000],  # Limit text length
                job_description=job_description[:3000]
            )
            
            # Three-tier response normalization system
            parsed_result = await self._parse_llm_response(result, resume_keywords, job_keywords, semantic_score)
            
            return parsed_result
            
        except Exception as e:
            logger.error(f"LLM match analysis failed: {str(e)}, using fallback matching")
            return self._simple_keyword_match(resume_keywords, job_keywords, resume_text, job_description, semantic_score)
    
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
            normalized_result = self._normalize_match_result(parsed_result)
            # Apply semantic boost to LLM result if available
            if semantic_score > 0:
                normalized_result = self._apply_semantic_boost(normalized_result, semantic_score)
            return normalized_result
            
        except json.JSONDecodeError:
            logger.warning("Tier 1 failed: JSON parsing error, trying text extraction")
            
        # Tier 2: Extract from natural language using regex patterns
        try:
            extracted_result = self._extract_from_natural_language(raw_response, resume_keywords, job_keywords)
            logger.info("Tier 2: Successfully extracted from natural language")
            if semantic_score > 0:
                extracted_result = self._apply_semantic_boost(extracted_result, semantic_score)
            return extracted_result
            
        except Exception as e:
            logger.warning(f"Tier 2 failed: Text extraction error: {str(e)}")
            
        # Tier 3: Rule-based fallback with semantic enhancement
        logger.info("Tier 3: Using rule-based fallback matching")
        return self._simple_keyword_match(resume_keywords, job_keywords, "", "", semantic_score)
    
    def _normalize_match_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize LLM match result to ensure proper data types."""
        normalized = result.copy()
        
        # Convert string values to lists for strengths and improvements
        for field in ['strengths', 'improvements']:
            if field in normalized:
                value = normalized[field]
                if isinstance(value, str):
                    # Split string by common delimiters and clean up
                    items = []
                    for delimiter in ['\n', ';', '.', '|']:
                        if delimiter in value:
                            items = [item.strip() for item in value.split(delimiter) if item.strip()]
                            break
                    
                    # If no delimiters found, treat as single item
                    if not items:
                        items = [value.strip()] if value.strip() else []
                    
                    normalized[field] = items
                    logger.info(f"Converted {field} from string to list: {items}")
                elif not isinstance(value, list):
                    # Handle other non-list types
                    normalized[field] = [str(value)] if value else []
                    logger.info(f"Converted {field} from {type(value)} to list")
        
        # Ensure other required fields are lists
        for field in ['matched_keywords', 'missing_keywords']:
            if field in normalized and not isinstance(normalized[field], list):
                if isinstance(normalized[field], str):
                    normalized[field] = [item.strip() for item in normalized[field].split(',') if item.strip()]
                else:
                    normalized[field] = []
        
        # Ensure match_percentage is a number
        if 'match_percentage' in normalized:
            try:
                normalized['match_percentage'] = float(normalized['match_percentage'])
            except (ValueError, TypeError):
                logger.warning(f"Invalid match_percentage: {normalized['match_percentage']}, defaulting to 0")
                normalized['match_percentage'] = 0
        
        return normalized
    
    def _extract_from_natural_language(self, text: str, resume_keywords: List[str], job_keywords: List[str]) -> Dict[str, Any]:
        """Extract structured data from natural language LLM response using regex patterns."""
        import re
        
        # Initialize default structure
        result = {
            "match_percentage": 0,
            "matched_keywords": [],
            "missing_keywords": [],
            "strengths": [],
            "improvements": []
        }
        
        # Extract match percentage
        percentage_pattern = r'(\d+)%|\b(\d+)\s*percent'
        percentage_match = re.search(percentage_pattern, text, re.IGNORECASE)
        if percentage_match:
            percentage = int(percentage_match.group(1) or percentage_match.group(2))
            result["match_percentage"] = min(100, max(0, percentage))
        
        # Extract lists from common patterns
        # Look for bullet points, numbered lists, or comma-separated items
        def extract_list_items(section_text: str) -> List[str]:
            items = []
            # Split by common delimiters and clean
            for delimiter in ['\n•', '\n-', '\n*', '\n1.', '\n2.', '\n3.', ',']:
                if delimiter in section_text:
                    parts = section_text.split(delimiter)
                    items = [item.strip().strip('•-*0123456789. ') for item in parts if item.strip()]
                    break
            
            if not items:
                # Fallback: split by sentences or commas
                items = [item.strip() for item in re.split(r'[,.;]', section_text) if item.strip()]
            
            return items[:10]  # Limit to 10 items
        
        # Extract matched keywords section
        matched_section = re.search(r'match(?:ed|ing)?\s*(?:keywords?|skills?|terms?).*?:\s*(.*?)(?:\n\n|\nMissing|\nStrengths|\nImprovement|$)', text, re.IGNORECASE | re.DOTALL)
        if matched_section:
            result["matched_keywords"] = extract_list_items(matched_section.group(1))
        
        # Extract missing keywords section  
        missing_section = re.search(r'missing\s*(?:keywords?|skills?|terms?).*?:\s*(.*?)(?:\n\n|\nStrengths|\nImprovement|$)', text, re.IGNORECASE | re.DOTALL)
        if missing_section:
            result["missing_keywords"] = extract_list_items(missing_section.group(1))
        
        # Extract strengths section
        strengths_section = re.search(r'strengths?.*?:\s*(.*?)(?:\n\n|\nImprovement|\nMissing|$)', text, re.IGNORECASE | re.DOTALL)
        if strengths_section:
            result["strengths"] = extract_list_items(strengths_section.group(1))
        
        # Extract improvements section
        improvements_section = re.search(r'improvement|recommend.*?:\s*(.*?)(?:\n\n|$)', text, re.IGNORECASE | re.DOTALL)
        if improvements_section:
            result["improvements"] = extract_list_items(improvements_section.group(1))
        
        # Fallback to keyword inference if extraction failed
        if not result["matched_keywords"] and not result["missing_keywords"]:
            # Use simple keyword matching as backup
            resume_lower = [k.lower() for k in resume_keywords]
            job_lower = [k.lower() for k in job_keywords]
            matches = list(set(resume_lower) & set(job_lower))
            missing = [jk for jk in job_lower if jk not in matches]
            
            result["matched_keywords"] = [k for k in resume_keywords if k.lower() in matches][:15]
            result["missing_keywords"] = [k for k in job_keywords if k.lower() in missing][:15]
            
            if not result["match_percentage"]:
                result["match_percentage"] = int((len(matches) / len(job_lower)) * 100) if job_lower else 0
        
        return result
    
    def _apply_semantic_boost(self, result: Dict[str, Any], semantic_score: float) -> Dict[str, Any]:
        """Apply semantic similarity boost to LLM analysis results."""
        if semantic_score > 0:
            current_percentage = result.get("match_percentage", 0)
            keyword_score = current_percentage / 100.0
            
            # Combine keyword-based result (70%) with semantic similarity (30%)
            boosted_score = (keyword_score * 0.7) + (semantic_score * 0.3)
            result["match_percentage"] = int(boosted_score * 100)
            
            # Add semantic analysis to strengths if significant
            if semantic_score > 0.6:
                if "strengths" not in result:
                    result["strengths"] = []
                result["strengths"].append(f"Strong semantic alignment between resume content and job requirements (similarity: {semantic_score:.1%})")
            
            logger.info(f"Applied semantic boost: {keyword_score:.3f} → {boosted_score:.3f}")
        
        return result
    
    def _simple_keyword_match(
        self,
        resume_keywords: List[str],
        job_keywords: List[str],
        resume_text: str,
        job_description: str,
        semantic_score: float = 0.0
    ) -> Dict[str, Any]:
        """Simple keyword matching as fallback when LLM fails."""
        # Convert to lowercase for case-insensitive matching
        resume_keywords_lower = [k.lower() for k in resume_keywords]
        job_keywords_lower = [k.lower() for k in job_keywords]
        resume_text_lower = resume_text.lower()
        
        # Find exact matches
        exact_matches = list(set(resume_keywords_lower) & set(job_keywords_lower))
        
        # Find partial matches (job keywords that appear in resume text)
        partial_matches = []
        for jk in job_keywords_lower:
            if jk not in exact_matches and jk in resume_text_lower:
                partial_matches.append(jk)
        
        # Combine matches
        all_matches = exact_matches + partial_matches
        missing_keywords = [jk for jk in job_keywords_lower if jk not in all_matches]
        
        # Calculate hybrid match percentage (keywords + semantic)
        if job_keywords_lower:
            keyword_match = (len(all_matches) / len(job_keywords_lower))
            # Combine keyword matching (70%) with semantic similarity (30%)
            hybrid_score = (keyword_match * 0.7) + (semantic_score * 0.3)
            match_percentage = int(hybrid_score * 100)
            logger.info(f"Hybrid scoring: keyword={keyword_match:.3f}, semantic={semantic_score:.3f}, final={hybrid_score:.3f}")
        else:
            match_percentage = int(semantic_score * 100) if semantic_score > 0 else 0
        
        # Generate basic feedback
        strengths = []
        if exact_matches:
            strengths.append(f"Strong keyword matches: {', '.join(exact_matches[:5])}")
        if partial_matches:
            strengths.append(f"Relevant skills found: {', '.join(partial_matches[:3])}")
        if not strengths:
            strengths.append("Resume contains relevant experience")
        
        improvements = []
        if missing_keywords:
            improvements.append(f"Consider adding: {', '.join(missing_keywords[:5])}")
        if match_percentage < 60:
            improvements.append("Focus on including more job-specific keywords")
        
        return {
            "match_percentage": match_percentage,
            "matched_keywords": [k for k in resume_keywords if k.lower() in all_matches],
            "missing_keywords": [k for k in job_keywords if k.lower() in missing_keywords],
            "strengths": strengths,
            "improvements": improvements
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
