from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
import sys
import tempfile
import os

VIDEO_ID = "eVFzbxmKNUw"  # The ID from your screenshot

def test_api():
    print("\n--- TEST 1: YouTubeTranscriptApi ---")
    try:
        # Adaptation for this environment's version
        if hasattr(YouTubeTranscriptApi, 'list_transcripts'):
            print("Standard list_transcripts exists")
            t_list = YouTubeTranscriptApi.list_transcripts(VIDEO_ID)
        else:
            print("Using instance-based .list()")
            api = YouTubeTranscriptApi()
            t_list = api.list(VIDEO_ID)
            
        print("Transcript List Found!")
        for t in t_list:
            # Check if t has attributes or is a dict
            lang = getattr(t, 'language_code', 'unknown')
            is_gen = getattr(t, 'is_generated', 'unknown')
            print(f" - [{lang}] Generated: {is_gen}")
    except Exception as e:
        print(f"FAILED: {e}")

def test_ytdlp_simple():
    print("\n--- TEST 2: yt-dlp (Simple) ---")
    try:
        ydl_opts = {
            'skip_download': True, 
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={VIDEO_ID}", download=False)
            if 'subtitles' in info:
                print(f"Manual Subs: {list(info['subtitles'].keys())}")
            if 'automatic_captions' in info:
                print(f"Auto Subs: {list(info['automatic_captions'].keys())}")
    except Exception as e:
        print(f"FAILED: {e}")

def test_ytdlp_advanced():
    print("\n--- TEST 3: yt-dlp (Robust Simulation) ---")
    try:
        # Check for cookies file
        cookie_file = "cookies.txt" if os.path.exists("cookies.txt") else None
        
        opts = {
            'skip_download': True, 
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'cookiefile': cookie_file,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
             info = ydl.extract_info(f"https://www.youtube.com/watch?v={VIDEO_ID}", download=False)
             print(f"Extraction Success for: {info.get('title')}")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    test_api()
    test_ytdlp_simple()
    test_ytdlp_advanced()
