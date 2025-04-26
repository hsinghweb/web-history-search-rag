import google.generativeai as genai
import numpy as np
from scipy.spatial.distance import cosine
from dotenv import load_dotenv
import os

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def get_embedding(text: str, task="retrieval_document") -> np.ndarray:
    model = "models/embedding-001"
    result = genai.embed_content(
        model=model,
        content=text,
        task_type=task
    )
    return np.array(result["embedding"], dtype=np.float32)

# 🎯 Phrases to compare
sentences = [
    "How does AlphaFold work?",
    "How do proteins fold?",
    "What is the capital of France?",
    "Explain how neural networks learn."
]

# 🧠 Get embeddings
embeddings = [get_embedding(s) for s in sentences]

# 🔁 Compare all pairs using cosine similarity
def cosine_similarity(v1, v2):
    return 1 - cosine(v1, v2)  # 1 = perfect match

print("🔍 Semantic Similarity Matrix:\n")
for i in range(len(sentences)):
    for j in range(i + 1, len(sentences)):
        sim = cosine_similarity(embeddings[i], embeddings[j])
        print(f"\"{sentences[i]}\" ↔ \"{sentences[j]}\" → similarity = {sim:.3f}")
