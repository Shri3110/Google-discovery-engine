import os
import json
import time
import logging
import statistics
from datetime import datetime
from groq import Groq
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class ExtractionExperiment:
    def __init__(self):
        self.base_dir = r"c:\Google discovery engine"
        self.experiment_dir = os.path.join(self.base_dir, "experiment_zone")
        os.makedirs(self.experiment_dir, exist_ok=True)
        
        self.input_file = os.path.join(self.base_dir, "processed_zone", "filtered_candidates.json")
        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY", "mock_key"))
        
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

    def validate_schema(self, result):
        corrected = False
        for field, allowed in self.enums.items():
            val = result.get(field)
            if val is not None and val not in allowed:
                result[field] = None
                result[f"{field}_validation_issue"] = True
                corrected = True
        return corrected

    def run_config(self, config_name, model, max_tokens, records, concurrency=1):
        logging.info(f"--- RUNNING CONFIG {config_name}: {model}, max_tokens={max_tokens} ---")
        
        results = []
        metrics = {
            "successful_requests": 0,
            "json_errors": 0,
            "429_errors": 0,
            "other_errors": 0,
            "latencies": [],
            "schema_corrected_count": 0,
            "null_fields": 0,
            "total_fields": 0
        }
        
        start_time = time.time()
        
        for r in records:
            user_prompt = f"User Feedback:\n\"{r['text']}\""
            
            # Simple retry loop to capture 429s without abstracting them away too much
            attempts = 0
            success = False
            
            while attempts < 3 and not success:
                attempts += 1
                req_start = time.time()
                try:
                    response = self.client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        model=model,
                        temperature=0.0,
                        max_tokens=800,
                        response_format={"type": "json_object"}
                    )
                    
                    req_end = time.time()
                    latency = req_end - req_start
                    metrics["latencies"].append(latency)
                    
                    raw_response = response.choices[0].message.content
                    
                    # Parse JSON
                    try:
                        parsed = json.loads(raw_response)
                        json_valid = True
                    except json.JSONDecodeError:
                        parsed = {}
                        json_valid = False
                        metrics["json_errors"] += 1
                        
                    res_obj = {
                        "experiment_id": config_name,
                        "model_name": model,
                        "max_tokens": max_tokens,
                        "concurrency": concurrency,
                        "source_record_id": r["id"],
                        "original_text": r["text"],
                        "raw_model_response": raw_response,
                        "parsed_extraction": parsed,
                        "latency": latency,
                        "api_status": 200
                    }
                    
                    # Schema Validation
                    corrected = self.validate_schema(parsed)
                    if corrected:
                        metrics["schema_corrected_count"] += 1
                        
                    res_obj["schema_validation_result"] = "corrected" if corrected else "valid"
                    
                    # Count nulls in parsed (excluding metadata fields we just added)
                    fields_to_check = ["is_retrieval_failure", "search_behavior", "failure_stage", "outcome", "photo_type", "verbatim_quote"]
                    for f in fields_to_check:
                        metrics["total_fields"] += 1
                        if parsed.get(f) is None:
                            metrics["null_fields"] += 1
                    
                    results.append(res_obj)
                    metrics["successful_requests"] += 1
                    success = True
                    
                except Exception as e:
                    if "429" in str(e):
                        metrics["429_errors"] += 1
                        logging.warning(f"429 on {r['id']}, attempt {attempts}")
                        time.sleep(2) # Backoff
                    else:
                        metrics["other_errors"] += 1
                        logging.error(f"Other error on {r['id']}: {e}")
                        break
                        
        total_time = time.time() - start_time
        metrics["total_elapsed_time"] = total_time
        metrics["requests_per_minute"] = (metrics["successful_requests"] / total_time) * 60 if total_time > 0 else 0
        
        if metrics["latencies"]:
            metrics["avg_latency"] = statistics.mean(metrics["latencies"])
            metrics["median_latency"] = statistics.median(metrics["latencies"])
        else:
            metrics["avg_latency"] = 0
            metrics["median_latency"] = 0
            
        with open(os.path.join(self.experiment_dir, f"{config_name}_results.json"), 'w', encoding='utf-8') as f:
            json.dump({"metrics": metrics, "results": results}, f, indent=2)
            
        return metrics

    def run(self):
        with open(self.input_file, 'r', encoding='utf-8') as f:
            all_records = json.load(f)
            
        # Get 5 deterministic records far away from the first few to avoid previous 38
        sample_records = all_records[200:205]
        logging.info(f"Loaded {len(sample_records)} sample records for experiment.")
        
        metrics_a = self.run_config("CONFIG_A", "openai/gpt-oss-120b", 800, sample_records)
        time.sleep(5) # Let rate limits cool down
        metrics_b = self.run_config("CONFIG_B", "openai/gpt-oss-20b", 800, sample_records)
        
        print("\n=== THROUGHPUT EXPERIMENT RESULTS ===")
        print(f"{'Metric':<30} | {'gpt-oss-120b (Config A)':<25} | {'gpt-oss-20b (Config B)':<25}")
        print("-" * 85)
        keys = ["successful_requests", "429_errors", "other_errors", "json_errors", "schema_corrected_count"]
        for k in keys:
            print(f"{k:<30} | {metrics_a[k]:<25} | {metrics_b[k]:<25}")
            
        print(f"{'requests_per_minute':<30} | {metrics_a['requests_per_minute']:<25.2f} | {metrics_b['requests_per_minute']:<25.2f}")
        print(f"{'avg_latency (s)':<30} | {metrics_a['avg_latency']:<25.2f} | {metrics_b['avg_latency']:<25.2f}")
        print(f"{'median_latency (s)':<30} | {metrics_a['median_latency']:<25.2f} | {metrics_b['median_latency']:<25.2f}")
        print(f"{'total_elapsed_time (s)':<30} | {metrics_a['total_elapsed_time']:<25.2f} | {metrics_b['total_elapsed_time']:<25.2f}")
        
        null_rate_a = (metrics_a["null_fields"] / metrics_a["total_fields"]) * 100 if metrics_a["total_fields"] > 0 else 0
        null_rate_b = (metrics_b["null_fields"] / metrics_b["total_fields"]) * 100 if metrics_b["total_fields"] > 0 else 0
        print(f"{'null_rate %':<30} | {null_rate_a:<25.2f} | {null_rate_b:<25.2f}")
        
        # Estimate for 2958 records
        est_a = (2958 / metrics_a['requests_per_minute']) if metrics_a['requests_per_minute'] > 0 else float('inf')
        est_b = (2958 / metrics_b['requests_per_minute']) if metrics_b['requests_per_minute'] > 0 else float('inf')
        print(f"{'Est. 2958 Time (mins)':<30} | {est_a:<25.2f} | {est_b:<25.2f}")

if __name__ == "__main__":
    ex = ExtractionExperiment()
    ex.run()
