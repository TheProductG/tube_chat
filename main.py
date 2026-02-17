from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import json
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

app = FastAPI()

# Move inits inside a flag to avoid repeated execution in serverless
initialized = False

@app.on_event("startup")
async def startup_event():
    global initialized
    if not initialized:
        init_db()
        try:
            # Only init Pinecone if keys are present
            if os.getenv("PINECONE_API_KEY"):
                vector_db.init_pinecone()
        except:
            pass
        initialized = True

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

class UploadTranscriptRequest(BaseModel):
    video_id: str
    url: str
    transcript: str

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.post("/upload-transcript")
async def upload_transcript(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload a pre-fetched transcript JSON file.
    Use the local fetch_transcript_local.py script to generate this file.
    """
    try:
        # Read the uploaded file
        contents = await file.read()
        data = json.loads(contents.decode('utf-8'))
        
        video_id = data.get('video_id')
        transcript = data.get('transcript')
        url = data.get('url', f"https://www.youtube.com/watch?v={video_id}")
        
        if not video_id or not transcript:
            raise HTTPException(status_code=400, detail="Invalid transcript file. Must contain 'video_id' and 'transcript'.")
        
        # Check if already exists
        try:
            cached_video = db.query(Video).filter(Video.video_id == video_id).first()
            if cached_video:
                return {
                    "video_id": video_id,
                    "transcript": cached_video.transcript,
                    "summary": cached_video.summary,
                    "cached": True,
                    "message": "This video was already analyzed."
                }
        except Exception as e:
            print(f"DB Query error: {e}")
        
        # Generate summary
        summary = generate_summary(transcript)
        
        # Index in vector DB
        try:
            if os.getenv("PINECONE_API_KEY"):
                chunks = chunk_text(transcript)
                embeddings = get_embeddings(chunks)
                vector_db.index_transcript(video_id, chunks, embeddings)
        except Exception as e:
            print(f"Indexing error: {e}")
        
        # Save to database
        try:
            new_video = Video(video_id=video_id, transcript=transcript, summary=summary)
            db.add(new_video)
            db.commit()
        except Exception as e:
            print(f"DB Save error: {e}")
        
        return {
            "video_id": video_id,
            "transcript": transcript,
            "summary": summary,
            "cached": False,
            "message": "Transcript uploaded and analyzed successfully!"
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing transcript: {str(e)}")

@app.post("/analyze")
async def analyze_video(request: AnalyzeRequest, db: Session = Depends(get_db)):
    video_id = extract_video_id(request.url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")
    
    try:
        cached_video = db.query(Video).filter(Video.video_id == video_id).first()
        if cached_video:
            return {
                "video_id": video_id,
                "transcript": cached_video.transcript,
                "summary": cached_video.summary,
                "cached": True
            }
    except Exception as e:
        print(f"DB Query error: {e}")

    transcript = get_transcript(video_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found.")
    
    summary = generate_summary(transcript)
    
    try:
        if os.getenv("PINECONE_API_KEY"):
            chunks = chunk_text(transcript)
            embeddings = get_embeddings(chunks)
            vector_db.index_transcript(video_id, chunks, embeddings)
    except Exception as e:
        print(f"Indexing error: {e}")

    try:
        new_video = Video(video_id=video_id, transcript=transcript, summary=summary)
        db.add(new_video)
        db.commit()
    except Exception as e:
        print(f"DB Save error: {e}")
    
    return {
        "video_id": video_id,
        "transcript": transcript,
        "summary": summary,
        "cached": False
    }

@app.post("/chat")
async def chat_about_video(request: ChatRequest):
    try:
        query_embeddings = get_embeddings([request.question])
        if not query_embeddings:
            raise Exception("Embedding failed")
            
        context_chunks = vector_db.search_chunks(query_embeddings[0], request.video_id)
        if not context_chunks:
            return {"answer": "I couldn't find enough context. Try re-analyzing the video."}

        answer = answer_with_context(context_chunks, request.question, request.history)
        return {"answer": answer}
    except Exception as e:
        return {"answer": f"Error: {str(e)}"}

# Serve static files for the frontend (Crucial for Render/Railway/HF)
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="static", html=True), name="static")
