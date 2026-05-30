import chromadb
import os
from sentence_transformers import SentenceTransformer

# Initialise ChromaDB with persistent storage
client = chromadb.PersistentClient(path="./chroma_db")

# Delete collection if it exists so we start clean
try:
    client.delete_collection("5g_knowledge_base")
except:
    pass

collection = client.create_collection(
    name="5g_knowledge_base",
    metadata={"description": "5G NetOps knowledge base"}
)

# Load embedding model
# This converts text into vectors ChromaDB can search
model = SentenceTransformer('all-MiniLM-L6-v2')

def ingest_folder(folder_path, tag):
    documents = []
    ids = []
    embeddings = []
    metadatas = []
    
    for filename in os.listdir(folder_path):
        if filename.endswith('.txt'):
            filepath = os.path.join(folder_path, filename)
            with open(filepath, 'r') as f:
                content = f.read()
            
            doc_id = f"{tag}_{filename}"
            embedding = model.encode(content).tolist()
            
            documents.append(content)
            ids.append(doc_id)
            embeddings.append(embedding)
            metadatas.append({"source": filename, "type": tag})
            
            print(f"Ingested: {doc_id}")
    
    collection.add(
        documents=documents,
        ids=ids,
        embeddings=embeddings,
        metadatas=metadatas
    )

# Ingest legitimate documents first
print("Ingesting legitimate documents...")
ingest_folder("data/legitimate", "legitimate")

# Ingest poisoned document
print("Ingesting poisoned document...")
ingest_folder("data/poisoned", "poisoned")

print(f"\nTotal documents in knowledge base: {collection.count()}")
print("Ingestion complete.")
