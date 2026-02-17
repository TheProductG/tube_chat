import re
import os
import json
import tempfile
import traceback
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp

def extract_video_id(url):
    """
    Extracts the video ID from various YouTube URL formats.
    """
    regex = r"(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^\"&?\/\s]{11})"
    match = re.search(regex, url)
    if match:
        return match.group(1)
    return None

def get_transcript(video_id):
    """
    Fetches the transcript for a given YouTube video ID.
    Uses a direct InnerTube API approach which is more resilient to IP blocks.
    """
    print(f"Fetching transcript for {video_id}...")
    
    # Method 1: Standard API with proxies disabled (often helps in cloud)
    try:
        # iterate through all available transcripts
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id, proxies=None)
        
        # Try to find english manually created first
        try:
           transcript = transcript_list.find_manually_created_transcript(['en', 'en-US', 'en-GB'])
        except:
           # fallback to any english
           try:
               transcript = transcript_list.find_generated_transcript(['en', 'en-US'])
           except:
               # fallback to ANY transcript and translate it (last resort)
               transcript = next(iter(transcript_list))
               if not transcript.is_translatable:
                   print("Transcript found but not translatable.")
               # Optionally translate to english if needed, but for now just return it
        
        transcript_data = transcript.fetch()
        return " ".join([item['text'] for item in transcript_data])
            
    except Exception as e:
        print(f"Primary method failed: {e}")

    # Method 2: yt-dlp with specific 'ios' client (often less blocked)
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            ydl_opts = {
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en.*'],
                'outtmpl': os.path.join(tmp_dir, 'sub'),
                'quiet': True,
                # Use iOS client which is rarely blocked
                'extractor_args': {'youtube': {'player_client': ['ios']}},
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)
                
                files = os.listdir(tmp_dir)
                vtt_files = [f for f in files if f.endswith('.vtt')]
                
                if vtt_files:
                    with open(os.path.join(tmp_dir, vtt_files[0]), 'r', encoding='utf-8') as f:
                        return clean_vtt(f.read())

    except Exception as e:
        print(f"Secondary method failed: {e}")

    return None

def clean_vtt(vtt_text):
    """
    Cleans VTT subtitle content into plain readable text.
    Handles overlapping lines and complex VTT tags.
    """
    # Remove header
    vtt_text = re.sub(r'WEBVTT', '', vtt_text)
    vtt_text = re.sub(r'Kind:.*', '', vtt_text)
    vtt_text = re.sub(r'Language:.*', '', vtt_text)
    
    # Remove timestamps and metadata lines
    # Pattern for timestamps: 00:00:00.000 --> 00:00:00.000 align:start position:0%
    lines = vtt_text.split('\n')
    text_content = []
    
    for line in lines:
        line = line.strip()
        if not line: continue
        if '-->' in line: continue
        if line.isdigit(): continue # Skip potential line numbers
        
        # Remove HTML-like tags (e.g., <c>, <u>, etc.)
        line = re.sub(r'<[^>]+>', '', line)
        
        # Clean special VTT character codes if any
        line = line.replace('&nbsp;', ' ')
        
        if line:
            text_content.append(line)
    
    # deduplicate adjacent identical lines (vtt often repeats lines for dynamic updates)
    final_lines = []
    for line in text_content:
        # Avoid exact duplicates or very minor variations that are adjacent
        if not final_lines or (line != final_lines[-1] and line not in final_lines[-1] and final_lines[-1] not in line):
            # Only add if it's not a subset of the previous or vice-versa (rolling captions)
            final_lines.append(line)
        elif len(line) > len(final_lines[-1]):
            # If the new line is longer (fuller version of same text), replace the old one
            final_lines[-1] = line
            
    return " ".join(final_lines)
