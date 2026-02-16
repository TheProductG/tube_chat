from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from services.youtube import extract_video_id, get_transcript
from services.openai_service import (
    generate_summary, 
    get_embeddings, 
    answer_with_context, 
    chunk_text
)
import database
from database import Video, get_db, init_db
import vector_db
import os

# Initialize database
init_db()
try:
    vector_db.init_pinecone()
except Exception as e:
    print(f"Pinecone init failed: {e}")

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    url: str

class ChatRequest(BaseModel):
    video_id: str
    question: str
    history: List[dict]

@app.post("/analyze")
async def analyze_video(request: AnalyzeRequest, db: Session = Depends(get_db)):
    video_id = extract_video_id(request.url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")
    
    # Check if video is already in SQLite (metadata/cache)
    cached_video = db.query(Video).filter(Video.video_id == video_id).first()
    
    # If in DB, we still want to return the data. 
    # Note: With ChromaDB, we index once.
    if cached_video:
        return {
            "video_id": video_id,
            "transcript": cached_video.transcript,
            "summary": cached_video.summary,
            "cached": True
        }
    
    # Fetch transcript
    transcript = get_transcript(video_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found.")
    
    # Generate summary
    summary = generate_summary(transcript)
    
    # Index in Pinecone (RAG)
    try:
        chunks = chunk_text(transcript)
        embeddings = get_embeddings(chunks)
        vector_db.index_transcript(video_id, chunks, embeddings)
        print(f"Indexed {len(chunks)} chunks for {video_id} in Pinecone")
    except Exception as e:
        print(f"Failed to index in Pinecone: {e}")

    # Save to SQLite for fast metadata access
    new_video = Video(video_id=video_id, transcript=transcript, summary=summary)
    db.add(new_video)
    db.commit()
    
    return {
        "video_id": video_id,
        "transcript": transcript,
        "summary": summary,
        "cached": False
    }

@app.post("/chat")
async def chat_about_video(request: ChatRequest):
    # Use RAG with Pinecone
    try:
        # 1. Get embedding for the user's question
        query_embeddings = get_embeddings([request.question])
        if not query_embeddings:
            raise Exception("Failed to generate embedding for question")
            
        # 2. Search relevant chunks in Pinecone
        context_chunks = vector_db.search_chunks(query_embeddings[0], request.video_id)
        
        if not context_chunks:
            # Fallback if no chunks found (rare if indexed)
            return {"answer": "I couldn't find relevant sections to answer that. Try another question."}

        # 3. Answer using RAG
        answer = answer_with_context(context_chunks, request.question, request.history)
        return {"answer": answer}
        
    except Exception as e:
        print(f"Chat error: {e}")
        return {"answer": f"I encountered an error while searching for the answer: {str(e)}"}

# Serve static files for the frontend
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
