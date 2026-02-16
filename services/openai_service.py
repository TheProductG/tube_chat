import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_summary(transcript):
    """
    Generates a concise summary of the provided transcript using GPT.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes YouTube video transcripts. Provide a concise, professional summary with key bullet points."},
                {"role": "user", "content": f"Please summarize the following YouTube video transcript:\n\n{transcript}"}
            ],
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating summary: {e}")
        return "Sorry, I couldn't generate a summary at this time."

def get_embeddings(texts):
    """
    Converts a list of strings into a list of embeddings.
    """
    try:
        response = client.embeddings.create(
            input=texts,
            model="text-embedding-3-small"
        )
        return [item.embedding for item in response.data]
    except Exception as e:
        print(f"Error generating embeddings: {e}")
        return []

def answer_with_context(context_chunks, question, history):
    """
    Answers a question based on retrieved context chunks.
    """
    context_text = "\n\n".join(context_chunks)
    try:
        messages = [
            {"role": "system", "content": f"You are a helpful assistant that answers questions about a YouTube video based on relevant excerpts from its transcript. Use the provided context to answer accurately.\n\nRelevant Context:\n{context_text}"}
        ]
        
        for msg in history:
            messages.append(msg)
            
        messages.append({"role": "user", "content": question})
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=800
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error answering with context: {e}")
        return "I'm having trouble answering that right now."

def chunk_text(text, chunk_size=1000, overlap=200):
    """
    Splits text into overlapping chunks for better RAG retrieval.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - overlap)
    return chunks
