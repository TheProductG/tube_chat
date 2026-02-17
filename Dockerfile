# Use the official Python image
FROM python:3.14-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=7860

# Set the working directory
WORKDIR /app

# Install system dependencies for yt-dlp and psycopg2
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libpq-dev \
    gcc \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create a directory for temporary files (Vercel optimization still useful here)
RUN mkdir -p /tmp/videos && chmod 777 /tmp/videos

# Expose the port Hugging Face Spaces expects (7860)
EXPOSE 7860

# Command to run the application
# We use --port 7860 because that is the Hugging Face default
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
