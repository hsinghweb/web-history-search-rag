import google.generativeai as genai
import numpy as np
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

sentence = "How does AlphaFold work?"

response = genai.embed_content(
    model="models/embedding-001",  # Using the stable embedding model
    content=sentence,
    task_type="retrieval_document"
)

embedding_vector = np.array(response['embedding'], dtype=np.float32)

print(f" Vector length: {len(embedding_vector)}")
print(f" First 5 values: {embedding_vector[:5]}")
