import json
from storage.vector_store import VectorStoreManager
import os

store = VectorStoreManager()
questions = [
    'Why do users fail to find screenshots?',
    'What information do users remember when they cannot find a photo?',
    'Where in the retrieval journey do users struggle?',
    'What workarounds do users use when photo search does not work?'
]

for q in questions:
    res = store.search(q, n_results=5)
    print('\n==============================')
    print(f'QUESTION: {q}')
    
    docs = res.get('documents', [[]])[0]
    metas = res.get('metadatas', [[]])[0]
    
    print(f'Retrieved: {len(docs)}')
    for i in range(len(docs)):
        meta = metas[i] if isinstance(metas[i], dict) else json.loads(metas[i])
        print(f"ID: {meta.get('id')} | Source: {meta.get('source')} | Quote: {meta.get('verbatim_quote')}")
