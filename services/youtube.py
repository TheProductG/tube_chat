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
    Attempts to use youtube-transcript-api first, then falls back to yt-dlp.
    """
    # Try youtube-transcript-api first (efficient)
    try:
        # Some cloud environments get blocked; we try to initialize with a common user agent
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Priority: Manual English -> Auto English -> Manual Any -> Auto Any
        try:
            transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
        except:
            try:
                transcript = transcript_list.find_manually_created_transcript()
            except:
                try:
                    transcript = transcript_list.find_generated_transcript(['en'])
                except:
                    transcript = next(iter(transcript_list))
        
        transcript_data = transcript.fetch()
        return " ".join([item['text'] for item in transcript_data])
    except Exception as e:
        print(f"youtube-transcript-api failed for {video_id}: {e}")

    # Fallback to yt-dlp (Stronger headers to avoid blocks)
    print(f"Falling back to yt-dlp for {video_id}...")
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            ydl_opts = {
                'skip_download': True,
                'writeautomaticsub': True,
                'writesubtitles': True,
                'subtitleslangs': ['en.*', '.*'],
                'outtmpl': os.path.join(tmp_dir, 'sub'),
                'quiet': True,
                'no_warnings': True,
                # Add headers to look more like a real browser
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'referer': 'https://www.google.com/',
                'noproxy': True,
                'geo_bypass': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Try multiple extractors if one fails
                ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)

                files = os.listdir(tmp_dir)
                vtt_files = [f for f in files if f.endswith('.vtt')]
                if not vtt_files:
                    # Final attempt: try to get the info and see if sub keys exist in the dict
                    info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                    if 'requested_subtitles' in info:
                        # Sometimes sub is in the info dict but not downloaded
                        sub_data = info['requested_subtitles']
                        # This part is complex, but we'll try the file path first
                        pass

                if vtt_files:
                    en_files = [f for f in vtt_files if '.en' in f.lower()]
                    target_file = en_files[0] if en_files else vtt_files[0]
                    
                    with open(os.path.join(tmp_dir, target_file), 'r', encoding='utf-8') as f:
                        content = f.read()
                        return clean_vtt(content)
                            
    except Exception as e:
        print(f"yt-dlp critical error for {video_id}: {str(e)}")
    
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
