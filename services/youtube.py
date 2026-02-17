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
    Strategy 1: youtube-transcript-api (Instance Based) - For this specific version
    Strategy 2: yt-dlp with browser spoofing (Robust)
    Strategy 3: yt-dlp with cookies (if available)
    """
    print(f"--- Fetching transcript for {video_id} using robust methods ---")
    
    # Strategy 1: youtube-transcript-api
    try:
        transcript_data = None
        
        # Check for list_transcripts (Newer API - Static)
        if hasattr(YouTubeTranscriptApi, 'list_transcripts'):
            print("Using standard static YouTubeTranscriptApi...")
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        # Check for list (Instance API) <- This is what the user has locally
        elif hasattr(YouTubeTranscriptApi, 'list'):
            print("Using instance-based YouTubeTranscriptApi...")
            api = YouTubeTranscriptApi() 
            transcript_list = api.list(video_id)
        else:
            # Fallback to get_transcript directly (Simplest API)
            print("Using direct get_transcript...")
            transcript_data = YouTubeTranscriptApi.get_transcript(video_id)

        if not transcript_data and 'transcript_list' in locals():
            # Find English
            try:
                transcript = transcript_list.find_manually_created_transcript(['en', 'en-US'])
            except:
                try:
                    transcript = transcript_list.find_generated_transcript(['en', 'en-US'])
                except:
                    print("No English transcript found, trying first available...")
                    transcript = next(iter(transcript_list))
            transcript_data = transcript.fetch()
        
        if transcript_data:
            # Handle both objects (with .text) and dicts (with ['text'])
            parts = []
            for item in transcript_data:
                if hasattr(item, 'text'):
                    parts.append(item.text)
                elif isinstance(item, dict) and 'text' in item:
                    parts.append(item['text'])
                else:
                    parts.append(str(item))
            
            full_text = " ".join(parts)
            print(f"Success via youtube-transcript-api! Length: {len(full_text)}")
            return full_text

    except Exception as e:
        print(f"Strategy 1 (API) failed: {e}")

    # Strategy 2: yt-dlp with browser simulation
    print("Trying Strategy 2: yt-dlp (Browser Simulation)...")
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            ydl_opts = {
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                # Avoid en.* to reduce 429 risk, just stick to main English variants
                'subtitleslangs': ['en', 'en-US'],  
                'outtmpl': os.path.join(tmp_dir, 'sub'),
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': True, # CRITICAL: Don't crash if one sub fails
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'referer': 'https://www.youtube.com/',
            }
            
            # Use cookies if available locally (for debugging)
            if os.path.exists("cookies.txt"):
                ydl_opts['cookiefile'] = "cookies.txt"
                print("Using local cookies.txt")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)
                
            # Check for files
            filesPath = tmp_dir
            if not os.path.exists(filesPath):
                print("Temp dir not found")
                return None
                
            files = os.listdir(filesPath)
            vtt_files = [f for f in files if f.endswith('.vtt')]
            
            if vtt_files:
                # Prefer english manually created, then auto
                vtt_files.sort(key=len)
                
                target_file = vtt_files[0]
                for f in vtt_files:
                    if '.en' in f.lower():
                        target_file = f
                        break
                
                print(f"Found subtitle file: {target_file}")
                with open(os.path.join(filesPath, target_file), 'r', encoding='utf-8') as f:
                    return clean_vtt(f.read())
            else:
                print("yt-dlp ran but no .vtt files were saved.")

    except Exception as e:
        print(f"Strategy 2 (yt-dlp) failed: {e}")
        traceback.print_exc()

    print("--- All strategies failed ---")
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
