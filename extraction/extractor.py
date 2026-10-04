import os
import json
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from groq import Groq
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - EXTRACTOR - %(levelname)s - %(message)s')

class GroqRateLimitError(Exception):
    pass

class ExtractorPipeline:
    def __init__(self):
        # Using the available model on this key endpoint
        self.model = "openai/gpt-oss-120b"
        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY", "mock_key"))
        
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.input_file = os.path.join(self.base_dir, "processed_zone", "filtered_candidates.json")
        self.output_dir = os.path.join(self.base_dir, "extracted_zone")
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.system_prompt = """
You are a highly analytical AI that categorizes user feedback about photo retrieval failures into a strict JSON schema.
Your goal is to extract evidence-backed data. Do not infer emotions or facts not explicitly stated.

Extract the feedback into a JSON object matching this schema:
{
  "is_retrieval_failure": bool,
  "memory_cues_present": ["place", "time_rough", "time_exact", "person", "object", "event", "emotion", "visual_detail", "app_context"],
  "memory_cues_missing": ["exact_date", "exact_location", "search_keywords", "album_name", "who_was_in_it"],
  "search_behavior": "keyword_guess" | "manual_scroll" | "album_browse" | "date_range_guess" | "person_filter" | "gave_up",
  "failure_stage": "expression" | "interpretation" | "evaluation" | "recovery",
  "workaround_used": string or null,
  "emotional_intensity": integer 1-5,
  "outcome": "found_eventually" | "never_found" | "unclear",
  "verbatim_quote": string (max 25 words),
  "photo_type": "screenshot" | "document_receipt" | "candid_moment" | "posed_person_group" | "scenery_place" | "food" | "other"
}

Few-shot Example 1:
User: "I know I took a picture of my boarding pass yesterday, but when I search 'ticket' it just shows concert photos. I scrolled for 10 minutes and just gave up."
Output:
{
  "is_retrieval_failure": true,
  "memory_cues_present": ["object", "time_rough"],
  "memory_cues_missing": [],
  "search_behavior": "keyword_guess",
  "failure_stage": "interpretation",
  "workaround_used": "scrolled for 10 minutes",
  "emotional_intensity": 3,
  "outcome": "never_found",
  "verbatim_quote": "when I search 'ticket' it just shows concert photos",
  "photo_type": "document_receipt"
}
"""

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=60), 
        stop=stop_after_attempt(10),
        reraise=True
    )
    def extract_record(self, record):
        """Calls Groq with exponential backoff for 429s."""
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"User Feedback:\n{record['text']}"}
                ],
                model=self.model,
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            extracted = json.loads(content)
            
            # Merge original ID for traceability
            extracted['id'] = record['id']
            extracted['source'] = record['source']
            return extracted
            
        except Exception as e:
            # Check for rate limit / 429 to trigger Tenacity retry properly
            if "429" in str(e) or "rate limit" in str(e).lower():
                logging.warning(f"Rate limited on {record['id']}, backing off...")
                raise GroqRateLimitError(f"Rate limit: {e}")
            else:
                logging.error(f"Failed extraction on {record['id']}: {e}")
                return None

    def run_batch(self, limit=40):
        if not os.path.exists(self.input_file):
            logging.error(f"Input file not found: {self.input_file}")
            return
            
        with open(self.input_file, 'r', encoding='utf-8') as f:
            records = json.load(f)
            
        logging.info(f"Loaded {len(records)} candidate records. Processing {limit} records...")
        
        validation_set = records[:limit]
        results = []
        
        # Process sequentially to strictly avoid 429 Rate Limits on the LLM
        for i, record in enumerate(validation_set):
            res = self.extract_record(record)
            if res:
                results.append(res)
            
            if (i+1) % 5 == 0:
                logging.info(f"Processed {i+1}/{limit} records...")
            time.sleep(5) # Delay 5 seconds to respect quota
                    
        out_file = os.path.join(self.output_dir, f"extracted_validation_set.json")
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
            
        logging.info(f"Extraction complete. Saved {len(results)} records to {out_file}")

if __name__ == "__main__":
    pipeline = ExtractorPipeline()
    pipeline.run_batch(limit=40)
