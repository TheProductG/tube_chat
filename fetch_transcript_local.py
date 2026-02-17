"""
Local Transcript Fetcher for TubeChat AI
Run this script on your local machine to fetch YouTube transcripts.
It will save the transcript to a JSON file that you can upload to the web app.
"""

import sys
import json
from services.youtube import extract_video_id, get_transcript

def main():
    if len(sys.argv) < 2:
        print("Usage: python fetch_transcript_local.py <youtube_url>")
        print("Example: python fetch_transcript_local.py https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        sys.exit(1)
    
    url = sys.argv[1]
    video_id = extract_video_id(url)
    
    if not video_id:
        print(f"❌ Invalid YouTube URL: {url}")
        sys.exit(1)
    
    print(f"📹 Video ID: {video_id}")
    print(f"🔍 Fetching transcript...")
    
    transcript = get_transcript(video_id)
    
    if not transcript:
        print("❌ Failed to fetch transcript. Make sure the video has captions/subtitles.")
        sys.exit(1)
    
    # Save to JSON file
    output_file = f"transcript_{video_id}.json"
    data = {
        "video_id": video_id,
        "url": url,
        "transcript": transcript
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Success! Transcript saved to: {output_file}")
    print(f"📊 Transcript length: {len(transcript)} characters")
    print(f"\n💡 Next steps:")
    print(f"   1. Go to your TubeChat AI web app")
    print(f"   2. Click 'Upload Transcript'")
    print(f"   3. Select the file: {output_file}")

if __name__ == "__main__":
    main()
