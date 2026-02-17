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
    Fetches the transcript with robust fallbacks.
    Strategy 1: youtube-transcript-api (Direct)
    Strategy 2: youtube-transcript-api (List based - Instance or Static)
    Strategy 3: yt-dlp with browser spoofing
    """
    print(f"--- Fetching transcript for {video_id} ---")
    
    # Strategy 1: Direct get_transcript (Simplest/Fastest)
    try:
        print("Strategy 1: Direct API call...")
        transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
        if transcript_data:
            return process_transcript_data(transcript_data)
    except Exception as e:
        print(f"Strategy 1 failed: {e}")

    # Strategy 2: List-based API (Good for choosing English correctly)
    try:
        print("Strategy 2: List-based API...")
        transcript_list = None
        
        # Check for list_transcripts (Static - Newer)
        if hasattr(YouTubeTranscriptApi, 'list_transcripts'):
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        # Check for list (Instance - Older/Local version)
        elif hasattr(YouTubeTranscriptApi, 'list'):
            api = YouTubeTranscriptApi() 
            transcript_list = api.list(video_id)
            
        if transcript_list:
            # Try English variants first
            try:
                transcript = transcript_list.find_manually_created_transcript(['en', 'en-US'])
            except:
                try:
                    transcript = transcript_list.find_generated_transcript(['en', 'en-US'])
                except:
                    print("No English transcript found, taking first available...")
                    transcript = next(iter(transcript_list))
            
            transcript_data = transcript.fetch()
            if transcript_data:
                return process_transcript_data(transcript_data)
    except Exception as e:
        print(f"Strategy 2 failed: {e}")

    # Strategy 3: yt-dlp with browser simulation
    print("Strategy 3: yt-dlp (Browser Simulation)...")
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            ydl_opts = {
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en', 'en-US'],  
                'outtmpl': os.path.join(tmp_dir, 'sub'),
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': True,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'referer': 'https://www.youtube.com/',
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # We need to use download=True to trigger subtitle download even with skip_download=True
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
                
            if os.path.exists(tmp_dir):
                files = os.listdir(tmp_dir)
                vtt_files = [f for f in files if f.endswith('.vtt')]
                
                if vtt_files:
                    vtt_files.sort(key=len)
                    target_file = vtt_files[0]
                    for f in vtt_files:
                        if '.en' in f.lower():
                            target_file = f
                            break
                    
                    print(f"Found subtitle file: {target_file}")
                    with open(os.path.join(tmp_dir, target_file), 'r', encoding='utf-8') as f:
                        return clean_vtt(f.read())
            
            print("yt-dlp completed but no VTT files found.")

    except Exception as e:
        print(f"Strategy 3 (yt-dlp) failed: {e}")

    print("--- All transcript strategies exhausted ---")
    return None

def process_transcript_data(transcript_data):
    """Helper to convert API response to string."""
    parts = []
    for item in transcript_data:
        if hasattr(item, 'text'):
            parts.append(item.text)
        elif isinstance(item, dict) and 'text' in item:
            parts.append(item['text'])
        else:
            parts.append(str(item))
    
    full_text = " ".join(parts)
    print(f"Success! Transcript length: {len(full_text)}")
    return full_text

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
