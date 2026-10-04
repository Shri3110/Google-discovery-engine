import json
import os
import sys
import time
from groq import Groq
from storage.vector_store import VectorStoreManager
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
store = VectorStoreManager(collection_name="validation_genuine_v1")

def run_evaluation():
    # Load genuine dataset
    with open('extracted_zone/genuine_validation_set.json', 'r', encoding='utf-8') as f:
        records = json.load(f)
        
    print(f"A. Genuine LLM-extracted records: {len(records)}")
    
    unsupported = 0
    retrieval_incidents = 0
    memory_cues = 0
    screenshot_incidents = 0
    workarounds = 0
    
    for r in records:
        # Check unsupported (null or empty)
        fields = ['is_retrieval_failure', 'memory_cues_present', 'memory_cues_missing', 
                  'search_behavior', 'failure_stage', 'workaround_used', 'outcome', 'photo_type']
        for field in fields:
            val = r.get(field)
            if val is None or val == [] or val == "":
                unsupported += 1
                
        if r.get('is_retrieval_failure'):
            retrieval_incidents += 1
            if r.get('photo_type') and 'screenshot' in str(r.get('photo_type')).lower():
                screenshot_incidents += 1
                
        if r.get('memory_cues_present'):
            memory_cues += 1
            
        if r.get('workaround_used'):
            workarounds += 1
            
    print(f"B. Unsupported extraction fields: {unsupported}")
    print(f"C. Actual retrieval incidents: {retrieval_incidents}")
    print(f"D. Explicit memory cues: {memory_cues}")
    print(f"E. Screenshot-related retrieval incidents: {screenshot_incidents}")
    print(f"F. Actual workaround behavior: {workarounds}")
    print("\n--- PHASE 4 AUDIT TABLE ---")
    for r in records[:5]:
        print(f"ID: {r['record_id']} | Stage: {r.get('failure_stage')} | Quote: {r.get('verbatim_quote')}")
    print("---------------------------\n")

    questions = [
        "Why do users fail to find screenshots?",
        "What information do users remember when they cannot find a photo?",
        "Where in the retrieval journey do users struggle?",
        "What workarounds do users use when photo search does not work?"
    ]
    
    print("\n--- PHASE 7/8/9 HYBRID RETRIEVAL & GATE ---")
    
    for q in questions:
        print(f"\nEvaluating: {q}")
        
        # 1. Intent parser (mocked logic for speed, but ideally LLM)
        # We will just use vector search but fetch 10 and gate them.
        res = store.search(q, n_results=10)
        docs = res.get('documents', [[]])[0]
        metas = res.get('metadatas', [[]])[0]
        
        direct_records = []
        indirect_records = []
        for meta in metas:
            meta_dict = meta if isinstance(meta, dict) else json.loads(meta)
            quote = meta_dict.get('verbatim_quote', '')
            original = meta_dict.get('original_text', quote)
            
            # 2. Relevance Gate
            prompt = f"Question: {q}\nEvidence: {original}\nClassify how this evidence supports the question.\nOutput ONLY one word: DIRECT, INDIRECT, or NONE.\nDIRECT: Explicitly mentions the specific subject (e.g. screenshots) and directly supports an answer.\nINDIRECT: Relates to the broader topic (e.g. general photo failure) but lacks the specific subject.\nNONE: Irrelevant."
            try:
                gate_res = client.chat.completions.create(
                    messages=[{"role": "system", "content": "You are a strict judge. Output exactly one word."}, {"role": "user", "content": prompt}],
                    model="openai/gpt-oss-20b",
                    temperature=0.0
                )
                label = gate_res.choices[0].message.content.strip().upper()
            except:
                label = "NONE"
                
            if "DIRECT" in label:
                direct_records.append(meta_dict)
            elif "INDIRECT" in label:
                indirect_records.append(meta_dict)
                
            time.sleep(0.5) # rate limit
            
        print(f"Direct records: {len(direct_records)}, Indirect records: {len(indirect_records)}")
        
        # 3. Synthesis
        evidence_context = ""
        if direct_records:
            evidence_context += "DIRECT EVIDENCE:\n" + json.dumps([{"id": r.get('id'), "quote": r.get('verbatim_quote')} for r in direct_records], indent=2) + "\n\n"
        if indirect_records:
            evidence_context += "INDIRECT / RELATED EVIDENCE:\n" + json.dumps([{"id": r.get('id'), "quote": r.get('verbatim_quote')} for r in indirect_records], indent=2)
            
        if not evidence_context:
            evidence_context = "No evidence found."

        sys_prompt = """You are a rigorous research analyst. Follow these STRICT rules:
1. Always start your response exactly with these three lines:
DIRECT EVIDENCE COUNT: <N>
INDIRECT/RELATED EVIDENCE COUNT: <N>
INSUFFICIENT EVIDENCE = YES/NO
(Set INSUFFICIENT EVIDENCE = YES if DIRECT EVIDENCE COUNT is 0).

2. If INSUFFICIENT EVIDENCE = YES, you MUST explicitly state that there is insufficient direct evidence in the current dataset. You may summarize the INDIRECT / RELATED EVIDENCE, but you MUST clearly label it as such, and you MUST NOT present it as directly answering the specific question (e.g. if asked about screenshots and you only have general photo evidence, do NOT say "Users fail to find screenshots because...").

3. Sample-size language MUST be strictly disciplined:
- If there is exactly 1 direct record, you MUST NOT generalize (e.g. no "Users often..." or "Users typically..."). You MUST use phrasing like "One documented case..." or "One documented workaround in the current sample was..."
- If there is a small number of direct records (2-4), use "In the current sample..."
- DO NOT use "typically", "usually", "primarily", "mainly", or "users often" unless you have many records supporting it.

4. EVERY substantive claim MUST cite the record ID (e.g. `(ID: xyz)`).
5. A claim requiring direct evidence cannot be generated from indirect evidence.
"""
        
        prompt = f"Research question: {q}\n\n{evidence_context}\n\nReturn concise Markdown findings based ONLY on this evidence following all rules."
        try:
            syn_res = client.chat.completions.create(
                messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}],
                model="openai/gpt-oss-20b",
                temperature=0.0
            )
            print("Synthesis:\n" + syn_res.choices[0].message.content)
        except Exception as e:
            print(f"Synthesis failed: {e}")

if __name__ == '__main__':
    run_evaluation()
