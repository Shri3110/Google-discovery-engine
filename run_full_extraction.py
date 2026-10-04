import os
import json
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from groq import Groq
from tenacity import retry, wait_exponential, stop_after_attempt
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ExtractorPipeline:
    def __init__(self):
        self.model = "openai/gpt-oss-120b"
        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY", "mock_key"))
        self.base_dir = r"c:\Google discovery engine"
        self.input_file = os.path.join(self.base_dir, "processed_zone", "sampled_candidates.json")
        self.output_file = os.path.join(self.base_dir, "extracted_zone", "full_corpus_extracted.json")
        self.failed_file = os.path.join(self.base_dir, "extracted_zone", "failed_records.json")
        
        self.system_prompt = """You are an expert product researcher. Extract structured data from the user feedback.
IMPORTANT: Only extract information that is EXPLICITLY SUPPORTED by the text.
If a field cannot be established from the text, return null (for strings/booleans) or [] (for arrays).
DO NOT INFER missing information. 
DO NOT guess failure stages or memory cues if they are not explicitly mentioned.

Output valid JSON matching this schema:
{
  "is_retrieval_failure": boolean,
  "memory_cues_present": [string],
  "memory_cues_missing": [string],
  "search_behavior": string,
  "failure_stage": string,
  "workaround_used": string,
  "emotional_intensity": integer (1-5),
  "outcome": string,
  "photo_type": string,
  "verbatim_quote": string (exact substring of the original text containing the evidence)
}"""

        self.enums = {
            "photo_type": {"screenshot", "document_receipt", "candid_moment", "posed_person_group", "scenery_place", "food", "other"},
            "search_behavior": {"keyword_guess", "manual_scroll", "album_browse", "date_range_guess", "person_filter", "gave_up"},
            "failure_stage": {"expression", "interpretation", "evaluation", "recovery"},
            "outcome": {"found_eventually", "never_found", "unclear"}
        }

    @retry(wait=wait_exponential(multiplier=1, min=2, max=60), stop=stop_after_attempt(5), reraise=True)
    def call_api(self, user_prompt):
        return self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model=self.model,
            temperature=0.0,
            max_tokens=800,
            response_format={"type": "json_object"}
        )

    def extract_record(self, record):
        original_text = record['text']
        user_prompt = f"User Feedback:\n\"{original_text}\""
        
        try:
            response = self.call_api(user_prompt)
            raw_response = response.choices[0].message.content
            parsed = json.loads(raw_response)
        except Exception as e:
            raise ValueError(f"API/Parsing error: {str(e)}")
            
        result = {
            "record_id": record["id"],
            "source": record["source"],
            "original_text": original_text,
            "verbatim_quote": parsed.get("verbatim_quote"),
            "is_retrieval_failure": parsed.get("is_retrieval_failure"),
            "memory_cues_present": parsed.get("memory_cues_present", []),
            "memory_cues_missing": parsed.get("memory_cues_missing", []),
            "search_behavior": parsed.get("search_behavior"),
            "failure_stage": parsed.get("failure_stage"),
            "workaround_used": parsed.get("workaround_used"),
            "emotional_intensity": parsed.get("emotional_intensity"),
            "outcome": parsed.get("outcome"),
            "photo_type": parsed.get("photo_type"),
            "model_name": self.model,
            "extraction_timestamp": datetime.utcnow().isoformat() + "Z",
            "raw_model_response": raw_response
        }
        
        # Schema Validation
        for field, allowed in self.enums.items():
            val = result.get(field)
            if val is not None and val not in allowed:
                result[field] = None
                result[f"{field}_validation_issue"] = True
                
        return result

    def run(self):
        with open(self.input_file, 'r', encoding='utf-8') as f:
            records = json.load(f)
            
        extracted = {}
        if os.path.exists(self.output_file):
            with open(self.output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for d in data:
                    extracted[d["record_id"]] = d
        
        failed = {}
        if os.path.exists(self.failed_file):
            with open(self.failed_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for d in data:
                    failed[d["record_id"]] = d

        pending_records = [r for r in records if r["id"] not in extracted and r["id"] not in failed]
        logging.info(f"Total: {len(records)}, Already extracted: {len(extracted)}, Pending: {len(pending_records)}")
        
        if not pending_records:
            logging.info("No records left to process.")
            return

        # Process sequentially (concurrency=1) with 3s pacing
        count = 0
        total_pending = len(pending_records)
        
        for r in pending_records:
            import time
            
            try:
                res = self.extract_record(r)
                extracted[r["id"]] = res
            except Exception as exc:
                logging.error(f"Record {r['id']} generated an exception: {exc}")
                failed[r["id"]] = {"record_id": r["id"], "error": str(exc)}
            
            count += 1
            if count % 10 == 0 or count == total_pending:
                logging.info(f"Processed {count}/{total_pending}")
                # Save batches
                with open(self.output_file, 'w', encoding='utf-8') as f:
                    json.dump(list(extracted.values()), f, indent=2)
                with open(self.failed_file, 'w', encoding='utf-8') as f:
                    json.dump(list(failed.values()), f, indent=2)
                    
            time.sleep(6)  # Pacing for 10 requests per minute (800 max_tokens -> 8000 TPM max)

if __name__ == "__main__":
    pipeline = ExtractorPipeline()
    pipeline.run()
