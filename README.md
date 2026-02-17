# TubeChat AI - YouTube Video Summarizer & Chatbot

An AI-powered application that analyzes YouTube videos and lets you chat with the content using GPT-4.

## 🚀 Features

- **Video Summarization**: Get AI-generated summaries of YouTube videos
- **Interactive Chat**: Ask questions about the video content
- **RAG Architecture**: Uses vector search for accurate, context-aware answers
- **Cloud Deployment**: Deployed on Railway with full API access

## 🌐 Live Demo

Visit the live app: [TubeChat AI on Railway](https://tubechat-ai-production.up.railway.app)

## 📝 Local Transcript Fetching

Due to YouTube's IP blocking of cloud providers, you may need to fetch transcripts locally and upload them.

### How to Use:

1. **Download the script**: Clone this repo or download `fetch_transcript_local.py`

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the script**:
   ```bash
   python fetch_transcript_local.py "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"
   ```

4. **Upload to the web app**:
   - Go to the [TubeChat AI web app](https://tubechat-ai-production.up.railway.app)
   - Click the **📤 Upload** button
   - Select the generated `transcript_VIDEO_ID.json` file
   - Start chatting!

### Example:

```bash
python fetch_transcript_local.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

This will create `transcript_dQw4w9WgXcQ.json` that you can upload to the web app.

## 🛠️ Tech Stack

- **Backend**: FastAPI, Python
- **AI**: OpenAI GPT-4o, Text Embeddings
- **Vector DB**: Pinecone
- **Database**: Supabase (PostgreSQL)
- **Transcript Fetching**: youtube-transcript-api, yt-dlp
- **Deployment**: Railway (Docker)

## 🔑 Environment Variables

If running locally, create a `.env` file:

```env
OPENAI_API_KEY=your_openai_key
PINECONE_API_KEY=your_pinecone_key
PINECONE_INDEX_NAME=youtube-chatbot
DATABASE_URL=your_supabase_connection_string
```

## 🏃 Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn main:app --reload --port 8000
```

Visit `http://localhost:8000`

## 📦 Deployment

This app is configured for Railway deployment with:
- `Dockerfile` for containerization
- `railway.json` for deployment config
- `start.sh` for dynamic PORT handling

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first.

## 📄 License

MIT

## 👤 Author

**Faizan Khan**
- GitHub: [@TheProductG](https://github.com/TheProductG)
