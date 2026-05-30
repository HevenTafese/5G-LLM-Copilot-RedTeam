import chromadb
import ollama
import logging
from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from datetime import datetime

# Logging setup sends to file for Splunk ingestion later
logging.basicConfig(
    filename='copilot.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

app = FastAPI()
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection("5g_knowledge_base")
embed_model = SentenceTransformer('all-MiniLM-L6-v2')

SYSTEM_PROMPT = """You are a 5G network operations assistant for TelecomLabCorp.
You help network operators manage AMF and SMF configurations, monitor subscriber 
records, and troubleshoot network slice issues. You have access to internal 
network documentation. Answer questions accurately based on the documentation 
provided to you."""

class Query(BaseModel):
    question: str

@app.post("/query")
def query_copilot(q: Query):
    # Convert question to embedding and retrieve relevant documents
    query_embedding = embed_model.encode(q.question).tolist()

    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )
    
    retrieved_docs = results['documents'][0]
    retrieved_sources = [m['source'] for m in results['metadatas'][0]]
    
    # Log the query and what was retrieved  this goes to Splunk
    logging.info(f"QUERY: {q.question}")
    logging.info(f"RETRIEVED_SOURCES: {retrieved_sources}")
    
    # Build context from retrieved documents
    context = "\n\n".join(retrieved_docs)
    
    # Send to Ollama with retrieved context
    response = ollama.chat(
        model='llama3.2',
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context from knowledge base:\n{context}\n\nQuestion: {q.question}"}
        ]
    )
    
    answer = response['message']['content']
    
    # Log the response
    logging.info(f"RESPONSE: {answer[:200]}")
    
    return {
        "question": q.question,
        "answer": answer,
        "sources_retrieved": retrieved_sources
    }

@app.get("/health")
def health():
    return {"status": "running", "documents": collection.count()}
