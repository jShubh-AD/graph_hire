import json
import logging
import io
from typing import List, Dict, Any
from google import genai
from pypdf import PdfReader
from fastapi import HTTPException

from app.core.config import settings
from app.schemas.resume import ParsedSkill
from app.core.prompts import RESUME_SKILL_EXTRACTION_SYSTEM_PROMPT, RESUME_SKILL_EXTRACTION_USER_PROMPT

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        if not self.api_key:
            logger.error("GEMINI_API_KEY not found in environment variables")
        self.client = genai.Client(api_key=self.api_key)

    def extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF using pypdf."""
        try:
            pdf_stream = io.BytesIO(pdf_bytes)
            reader = PdfReader(pdf_stream)
            
            extracted_text = ""
            for page in reader.pages:
                extracted_text += page.extract_text() + "\n"
            
            return extracted_text.strip()
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise HTTPException(status_code=400, detail="Could not read PDF file structure")

    async def parse_resume_skills(self, pdf_bytes: bytes, available_skills: List[Dict[str, Any]]) -> List[ParsedSkill]:
        """
        Extracts text from PDF bytes, then uses Gemini to map skills to the database.
        """
        if not self.api_key:
            raise HTTPException(status_code=500, detail="Gemini API key is missing")

        # 1. Extract text from PDF
        resume_text = self.extract_text_from_pdf(pdf_bytes)

        # 2. Format available skills for the prompt
        # Note: TigerGraph results use 'id' or 'v_id' depending on helper; 
        # get_all_skills_list returns {"id": int, "name": str}
        skills_formatted = "\n".join([f"ID: {s['id']}, Name: {s['name']}" for s in available_skills])
        
        user_prompt = RESUME_SKILL_EXTRACTION_USER_PROMPT.format(
            available_skills=skills_formatted,
            resume_text=resume_text[:8000] # Optimized context window to save tokens
        )

        try:
            # 3. Use gemini-1.5-flash (more stable for free tier)
            response = self.client.models.generate_content(
                model='gemini-2.5-flash-lite',
                contents=user_prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=RESUME_SKILL_EXTRACTION_SYSTEM_PROMPT,
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )

            result = json.loads(response.text)
            raw_extracted = result.get("extracted_skills", [])
            
            # 4. Map and Validate
            valid_ids = {s['id'] for s in available_skills}
            final_skills = []
            
            for item in raw_extracted:
                # Handle potential camelCase/snake_case variations from LLM
                sid = item.get('skill_id') or item.get('skillId')
                name = item.get('name') or item.get('skill')
                prof = item.get('proficiency', 0.5)
                
                if sid in valid_ids:
                    final_skills.append(ParsedSkill(
                        name=name,
                        skillId=int(sid),
                        proficiency=float(prof)
                    ))
            
            return final_skills
            
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            return []

ai_service = AIService()
