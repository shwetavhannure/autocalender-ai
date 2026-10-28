import json
import re
from google import genai
from google.genai import types

from config.settings import settings
from src.utils import clean_model_output, build_system_instruction

class ParserEngine:
    def __init__(self):
        """Initializes Google GenAI client connections using configuration settings."""
        if not settings.GEMINI_API_KEY:
            raise ValueError("Environment Mismatch: GEMINI_API_KEY value undefined inside configuration map!")
        
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_id = settings.LLM_MODEL_NAME
        print(f"AI Model Processing Initialized: {self.model_id}")

    def extract_event_details(self, email_body: str, subject: str = "") -> dict:
        """Extracts precise event metadata using robust text formatting to match reference console logs."""
        default_data = {
            "event": settings.DEFAULT_FALLBACK_STRING, 
            "iso_start": settings.DEFAULT_FALLBACK_STRING, 
            "venue": settings.DEFAULT_FALLBACK_STRING
        }
        
        if not email_body or not isinstance(email_body, str) or not email_body.strip():
            return default_data

        cleaned_text = email_body[:2000].replace("\n", " ")
        system_instruction = build_system_instruction()
        user_prompt_content = (
            f"Subject: {subject}\nEmail Body: {cleaned_text}\n\n"
            "Extract the event details and respond strictly in this plain text format without code blocks:\n"
            "EVENT: <title>\n"
            "ISO_START: <YYYY-MM-DDTHH:MM:SS or Year>\n"
            "VENUE: <location>"
        )

        try:
            # Official Google GenAI SDK Client Call using plain text output to prevent JSON truncation
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[user_prompt_content],
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.1,
                    max_output_tokens=400
                )
            )
            
            output_text = response.text
            if not output_text:
                return default_data
            
            print(f"[AI Raw Output]:\n{output_text.strip()}\n{'-'*40}")
            
            # Parse output using regular expressions matching reference project logs
            return self._parse_model_output(output_text)
            
        except Exception as e:
            print(f"LLM Token Inference Pipeline Aborted: {e}")
            return default_data

    def _parse_model_output(self, raw_output: str) -> dict:
        parsed_data = {}
        mappings = {
            "event": r"(?:EVENT|TITLE|NAME):\s*(.*)",
            "iso_start": r"ISO_START:\s*(.*)",
            "venue": r"VENUE:\s*(.*)"
        }

        for key, pattern in mappings.items():
            match = re.search(pattern, raw_output, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                value = re.sub(r'^\[|\]$', '', value)
                
                # Normalize venue if it captures massive multi-line dial-in blocks
                if key == "venue" and (len(value) > 60 or "zoom" in value.lower()):
                    value = "Online / Zoom Meeting"
                    
                parsed_data[key] = clean_model_output(value)
            else:
                parsed_data[key] = settings.DEFAULT_FALLBACK_STRING

        return parsed_data