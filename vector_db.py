import os
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

load_dotenv()

# Initialize Pinecone
api_key = os.getenv("PINECONE_API_KEY")
index_name = os.getenv("PINECONE_INDEX_NAME", "youtube-chatbot")

pc = Pinecone(api_key=api_key)

def init_pinecone():
    """
    Ensures the Pinecone index exists. Create it if it doesn't.
    """
    if index_name not in pc.list_indexes().names():
        print(f"Creating Pinecone index: {index_name}...")
        pc.create_index(
            name=index_name,
            dimension=1536, # Dimension for OpenAI text-embedding-3-small
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )
    return pc.Index(index_name)

def index_transcript(video_id, chunks, embeddings):
    """
    Upserts transcript chunks and their embeddings to the Pinecone cloud index.
    """
    index = pc.Index(index_name)
    vectors = []
    
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        vectors.append({
            "id": f"{video_id}_{i}",
            "values": embedding,
            "metadata": {
                "video_id": video_id,
                "text": chunk
            }
        })
    
    # Upsert in batches of 100 to be safe
    for j in range(0, len(vectors), 100):
        index.upsert(vectors=vectors[j:j+100])

def search_chunks(query_embedding, video_id, top_k=5):
    """
    Searches Pinecone for the most relevant chunks of a specific video.
    """
    index = pc.Index(index_name)
    
    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        filter={"video_id": {"$eq": video_id}},
        include_metadata=True
    )
    
    return [match.metadata['text'] for match in results.matches]
