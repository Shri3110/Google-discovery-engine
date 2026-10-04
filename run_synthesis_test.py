import json
import os
from groq import Groq
from storage.vector_store import VectorStoreManager

store = VectorStoreManager()
client = Groq(api_key=os.environ.get("GROQ_API_KEY", "mock_key"))

questions = [
    'Why do users fail to find screenshots?',
    'What information do users remember when they cannot find a photo?',
    'Where in the retrieval journey do users struggle?',
    'What workarounds do users use when photo search does not work?'
]

for q in questions:
    res = store.search(q, n_results=5)
    
    docs = res.get('documents', [[]])[0]
    metas = res.get('metadatas', [[]])[0]
    
    records_payload = []
    for meta in metas:
        meta_dict = meta if isinstance(meta, dict) else json.loads(meta)
        records_payload.append({
            "record_id": meta_dict.get("id"),
            "source": meta_dict.get("source"),
            "photo_type": meta_dict.get("photo_type"),
            "memory_cues_present": meta_dict.get("memory_cues_present", "[]"),
            "memory_cues_missing": meta_dict.get("memory_cues_missing", "[]"),
            "search_behavior": meta_dict.get("search_behavior"),
            "failure_stage": meta_dict.get("failure_stage"),
            "outcome": meta_dict.get("outcome"),
            "verbatim_quote": meta_dict.get("verbatim_quote")
        })

    evidence_context = json.dumps(records_payload, indent=2)

    prompt = f"""Research question:
{q}

Evidence:
{evidence_context}

Return concise Markdown with:

## Key Finding
## What Users Remember
## What They Forget
## Retrieval Failure
## Supporting Evidence
## Evidence Gaps"""

    system_msg = "You are a product research analyst analyzing real Google Photos user evidence.\n\nAnswer ONLY from the evidence provided below.\n\nDo not use outside knowledge.\nDo not invent user complaints.\nDo not invent quotes.\nDo not invent statistics.\n\nFor each finding:\n- explain what the evidence shows\n- distinguish what users remember from what they forget\n- identify the retrieval failure if supported\n- cite the record IDs\n\nIf the evidence does not support a conclusion, explicitly say so."
    
    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            model="openai/gpt-oss-20b",
            temperature=0.0
        )
        print(f"\n==============================\nQUESTION: {q}\n")
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"Error for question {q}: {e}")
