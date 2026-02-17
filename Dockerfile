# Use a stable Python version
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=7860

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libpq-dev \
    gcc \
    curl \
    gnupg \
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

# Make startup script executable
RUN chmod +x start.sh

# Command to run the application
# Railway provides PORT dynamically. Shell form allows $PORT expansion.
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
