from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Vercel Fix: Ensure we don't try to write to the root directory
if not DATABASE_URL:
    # Use /tmp for SQLite as a last-resort fallback (Vercel allows writing here)
    SQLALCHEMY_DATABASE_URL = "sqlite:////tmp/videos.db"
else:
    # Cloud Postgres (Supabase)
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
    SQLALCHEMY_DATABASE_URL = DATABASE_URL

# For Postgres, we don't need check_same_thread
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Video(Base):
    __tablename__ = "videos"
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String, unique=True, index=True)
    transcript = Column(Text)
    summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Database init warning: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
